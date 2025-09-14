import pdfplumber
import pandas as pd
import os
import logging
import hashlib
import shutil
import re
from datetime import datetime
from utils.file_utils import log_file_movement, generate_standardized_filename
from database_utils import db_connection

# --- CONFIGURACIÓN ---
DOCUMENT_TYPE = 'LINEA_CREDITO_BCH'

# Configuración de logging principal
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Logger para el estado de la ingesta
ingestion_status_logger = logging.getLogger('ingestion_status')
ingestion_status_logger.setLevel(logging.INFO)
if not ingestion_status_logger.handlers:
    status_file_handler = logging.FileHandler('ingestion_status.log')
    status_formatter = logging.Formatter('%(asctime)s - %(message)s')
    status_file_handler.setFormatter(status_formatter)
    ingestion_status_logger.addHandler(status_file_handler)

def calculate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_all_pdf_files(directory):
    pdf_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, filename))
    return pdf_files

def is_file_processed(conn, file_hash):
    """Verifica si un archivo con el mismo hash ya existe en la tabla de metadatos."""
    cursor = conn.cursor()
    query = "SELECT metadata_id FROM raw_metadatos_cartolas_bancarias WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone()
    # Si fetchone() devuelve algo, significa que el hash ya existe.
    if result:
        logging.info(f"Hash {file_hash} ya se encuentra en la base de datos. Omitiendo archivo.")
        return True
    return False

def get_source_id(conn, source_name='Banco de Chile - Línea de Crédito'):
    cursor = conn.cursor(buffered=True)
    query = "SELECT fuente_id FROM fuentes WHERE nombre_fuente = %s"
    cursor.execute(query, (source_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        insert_query = "INSERT INTO fuentes (nombre_fuente) VALUES (%s)"
        cursor.execute(insert_query, (source_name,))
        conn.commit()
        return cursor.lastrowid

def insert_metadata(conn, source_id, pdf_path, file_hash):
    cursor = conn.cursor()
    query = '''
    INSERT INTO raw_metadatos_documentos (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    '''
    values = (source_id, os.path.basename(pdf_path), file_hash, DOCUMENT_TYPE)
    cursor.execute(query, values)
    return cursor.lastrowid

def parse_and_clean_value(value):
    if not isinstance(value, str):
        return value if pd.notna(value) else 0.0
    cleaned_value = value.strip().replace('$', '').replace('.', '').replace(',', '.')
    if not cleaned_value or cleaned_value == '-':
        return 0.0
    try:
        return float(cleaned_value)
    except (ValueError, TypeError):
        return 0.0

def parse_linea_credito_pdf(pdf_path):
    logging.info(f"Iniciando parseo para: {pdf_path}")
    processed_transactions = []
    raw_transactions = []
    document_date = None
    initial_balance = None
    final_balance = None

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        
        date_match = re.search(r"HASTA\s*:\s*(\d{2}/\d{2}/(\d{4}))", full_text)
        if date_match:
            document_date = datetime.strptime(date_match.group(1), "%d/%m/%Y")
        else:
            logging.error(f"La fecha 'HASTA' no pudo ser determinada para {pdf_path}.")
            return None

        initial_match = re.search(r"SALDO\s+INICIAL\s+([\d\.,]+)", full_text)
        if initial_match:
            initial_balance = parse_and_clean_value(initial_match.group(1))

        final_match = re.search(r"SALDO\s+FINAL\s+([\d\.,]+)", full_text)
        if final_match:
            final_balance = parse_and_clean_value(final_match.group(1))

        if initial_balance is None or final_balance is None:
            logging.error(f"No se pudo determinar Saldo Inicial o Final para {pdf_path}")
            return None

        hasta_year, hasta_month = document_date.year, document_date.month
        in_transaction_block = False
        for line in full_text.split('\n'):
            logging.debug(f"LINEA RAW: '{line}'")
            if "SALDO INICIAL" in line:
                in_transaction_block = True
                logging.debug("INICIO DE BLOQUE DE TRANSACCIONES")
                continue
            if "SALDO FINAL" in line:
                in_transaction_block = False
                logging.debug("FIN DE BLOQUE DE TRANSACCIONES")
                continue
            
            line = line.strip()
            date_match = re.match(r'^(\d{2}/\d{2})', line)
            if not in_transaction_block or not date_match:
                continue

            logging.info(f"LINEA DE TRANSACCION IDENTIFICADA: {line}")

            date_str = date_match.group(1)
            
            # Regex para encontrar valores numericos que parecen dinero (con puntos como separadores de miles)
            number_values = re.findall(r'[\d\.]+\d', line)
            potential_numbers = [p for p in number_values if '/' not in p and p.count('.') > 0 or p.isdigit()]

            if len(potential_numbers) < 1:
                logging.warning(f"No se encontraron valores numéricos en la línea: {line}")
                continue

            raw_saldo = potential_numbers[-1]
            raw_cargo = ""
            raw_abono = ""
            desc_str = ""

            if len(potential_numbers) > 1:
                main_value = potential_numbers[-2]
                try:
                    main_value_pos = line.rfind(main_value)
                    desc_str = line[len(date_str):main_value_pos].strip()
                    
                    if "ABONO" in desc_str.upper() or "PAGO" in desc_str.upper():
                        raw_abono = main_value
                    else:
                        raw_cargo = main_value
                except Exception:
                    desc_str = "Error al parsear descripción"
                    raw_cargo = main_value
            else:
                desc_str = line[len(date_str):].replace(raw_saldo, '').strip()

            tx_day, tx_month = map(int, date_str.split('/'))
            correct_year = hasta_year if tx_month <= hasta_month else hasta_year - 1
            tx_date = pd.to_datetime(f"{tx_day}/{tx_month}/{correct_year}", format='%d/%m/%Y')

            processed_transactions.append({
                'fecha_transaccion': tx_date.strftime('%Y-%m-%d'), 'descripcion': desc_str.strip(),
                'cargos': parse_and_clean_value(raw_cargo), 'abonos': parse_and_clean_value(raw_abono)
            })
            raw_transactions.append({
                'FECHA DIA/MES': date_str, 'DETALLE DE TRANSACCION': desc_str.strip(),
                'MONTO CHEQUES O CARGOS': raw_cargo, 'MONTO DEPOSITOS O ABONOS': raw_abono, 'SALDO': raw_saldo
            })

    processed_df = pd.DataFrame(processed_transactions)
    raw_df = pd.DataFrame(raw_transactions)

    return {
        "raw_df": raw_df,
        "processed_df": processed_df,
        "document_date": document_date,
        "validation_data": {
            "tx_count": len(processed_df),
            "initial_balance_pdf": initial_balance,
            "final_balance_pdf": final_balance
        }
    }




def insert_raw_pdf_linea_credito_to_staging(conn, metadata_id, source_id, raw_df):
    cursor = conn.cursor()
    cols = ", ".join([f'`{col}`' for col in raw_df.columns])
    placeholders = ", ".join(["%s"] * len(raw_df.columns))
    query = f"INSERT INTO staging_linea_credito_banco_chile_pdf (metadata_id, fuente_id, {cols}) VALUES (%s, %s, {placeholders})"
    
    rows_to_insert = [tuple([metadata_id, source_id] + list(row)) for row in raw_df.itertuples(index=False)]
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Se insertaron {len(rows_to_insert)} filas en staging para metadata_id: {metadata_id}")

def validate_staging_data(conn, metadata_id, validation_data):
    cursor = conn.cursor()
    try:
        # 1. Validación de conteo
        expected_count = validation_data['tx_count']
        cursor.execute("SELECT COUNT(*) FROM staging_linea_credito_banco_chile_pdf WHERE metadata_id = %s", (metadata_id,))
        actual_count = cursor.fetchone()[0]
        count_valid = actual_count == expected_count
        logging.info(f"VALIDACIÓN CONTEO: ESPERADO={expected_count}, OBTENIDO={actual_count} -> {'ÉXITO' if count_valid else 'FALLO'}")

        if not count_valid:
            return False

        # 2. Validación de reconciliación
        initial_balance_pdf = validation_data['initial_balance_pdf']
        final_balance_pdf = validation_data['final_balance_pdf']

        # Sumar cargos y abonos desde la base de datos de staging
        # Se usa REPLACE anidado para manejar '1.234,56' -> '1234.56'
        query_sum_cargos = "SELECT SUM(CAST(REPLACE(REPLACE(`MONTO CHEQUES O CARGOS`, '.', ''), ',', '.') AS DECIMAL(15,2))) FROM staging_linea_credito_banco_chile_pdf WHERE metadata_id = %s AND `MONTO CHEQUES O CARGOS` != ''"
        cursor.execute(query_sum_cargos, (metadata_id,))
        sum_cargos_db = cursor.fetchone()[0] or 0.0
        
        query_sum_abonos = "SELECT SUM(CAST(REPLACE(REPLACE(`MONTO DEPOSITOS O ABONOS`, '.', ''), ',', '.') AS DECIMAL(15,2))) FROM staging_linea_credito_banco_chile_pdf WHERE metadata_id = %s AND `MONTO DEPOSITOS O ABONOS` != ''"
        cursor.execute(query_sum_abonos, (metadata_id,))
        sum_abonos_db = cursor.fetchone()[0] or 0.0

        calculated_final_balance = initial_balance_pdf + sum_abonos_db - sum_cargos_db
        reconciliation_valid = abs(calculated_final_balance - final_balance_pdf) < 0.01
        
        logging.info(f"VALIDACIÓN RECONCILIACIÓN: SALDO INICIAL PDF={initial_balance_pdf}, ABONOS DB={sum_abonos_db}, CARGOS DB={sum_cargos_db}")
        logging.info(f"CÁLCULO: {initial_balance_pdf} + {sum_abonos_db} - {sum_cargos_db} = {calculated_final_balance}")
        logging.info(f"COMPARACIÓN: CALCULADO={calculated_final_balance} vs. SALDO FINAL PDF={final_balance_pdf} -> {'ÉXITO' if reconciliation_valid else 'FALLO'}")

        return reconciliation_valid

    except Exception as e:
        logging.error(f"Error durante la validación de staging: {e}", exc_info=True)
        return False
    finally:
        cursor.close()

def insert_linea_credito_transactions(conn, metadata_id, source_id, transactions_df):
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_transacciones_linea_credito (
        metadata_id, fuente_id, fecha_transaccion, descripcion, cargos, abonos
    ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in transactions_df.iterrows():
        rows_to_insert.append((metadata_id, source_id, row.get('fecha_transaccion'),
            row.get('descripcion'), row.get('cargos'), row.get('abonos')))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones en raw_transacciones_linea_credito para metadata_id: {metadata_id}")

def move_file_to_processed(pdf_path, file_hash, document_type, document_period):
    processed_dir = os.path.join(os.path.dirname(pdf_path), 'procesados')
    os.makedirs(processed_dir, exist_ok=True)
    new_filename = generate_standardized_filename(
        document_type=document_type, document_period=document_period,
        file_hash=file_hash, original_filename=os.path.basename(pdf_path)
    )
    processed_filepath = os.path.join(processed_dir, new_filename)
    shutil.move(pdf_path, processed_filepath)
    logging.info(f"Archivo movido a {processed_filepath}")
    log_file_movement(pdf_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")

def main():
    pdf_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\linea de crédito'
    pdf_files = find_all_pdf_files(pdf_directory)
    
    if not pdf_files:
        logging.info(f"No se encontraron archivos PDF en: {pdf_directory}")
        return

    logging.info(f"Se encontraron {len(pdf_files)} archivos PDF.")

    with db_connection() as conn:
        source_id = get_source_id(conn)
        for pdf_path in pdf_files:
            file_hash = None
            try:
                file_hash = calculate_file_hash(pdf_path)
                print(f"DEBUG: Processing file with hash: {file_hash}") # Temporary debug print
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado, omitiendo: {os.path.basename(pdf_path)}")
                    continue

                parse_result = parse_linea_credito_pdf(pdf_path)

                if not parse_result:
                    ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Failed - Critical parsing error")
                    continue
                
                raw_df = parse_result["raw_df"]
                processed_df = parse_result["processed_df"]
                document_date = parse_result["document_date"]
                validation_data = parse_result["validation_data"]

                if not validation_data['tx_count'] > 0:
                    logging.info(f"No se encontraron transacciones en {os.path.basename(pdf_path)}. Moviendo archivo.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Processed - No transactions found")
                    move_file_to_processed(pdf_path, file_hash, DOCUMENT_TYPE, document_date)
                    continue

                conn.autocommit = False
                metadata_id = insert_metadata(conn, source_id, pdf_path, file_hash)
                insert_raw_pdf_linea_credito_to_staging(conn, metadata_id, source_id, raw_df)

                if not validate_staging_data(conn, metadata_id, validation_data):
                    logging.error(f"La validación de staging falló para {os.path.basename(pdf_path)}. Revirtiendo.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Failed - Staging validation failed")
                    conn.rollback()
                    continue
                
                insert_linea_credito_transactions(conn, metadata_id, source_id, processed_df)

                conn.commit()
                ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Processed Successfully")
                move_file_to_processed(pdf_path, file_hash, DOCUMENT_TYPE, document_date)

            except Exception as e:
                logging.error(f"Error procesando {os.path.basename(pdf_path)}: {e}", exc_info=True)
                if conn.in_transaction:
                    conn.rollback()

if __name__ == '__main__':
    main()
