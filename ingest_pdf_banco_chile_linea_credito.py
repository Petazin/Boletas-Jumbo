import pdfplumber
import pandas as pd
import os
import logging
import hashlib
import shutil
import re
from datetime import datetime
from utils.file_utils import log_file_movement
from database_utils import db_connection

# Configuración de logging principal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Logger para el estado de la ingesta
ingestion_status_logger = logging.getLogger('ingestion_status')
ingestion_status_logger.setLevel(logging.INFO)
if not ingestion_status_logger.handlers:
    status_file_handler = logging.FileHandler('ingestion_status.log')
    status_formatter = logging.Formatter('%(asctime)s - %(message)s')
    status_file_handler.setFormatter(status_formatter)
    ingestion_status_logger.addHandler(status_file_handler)

# Logger para depuración de extracción de PDF
pdf_debug_logger = logging.getLogger('pdf_debug')
pdf_debug_logger.setLevel(logging.DEBUG)
if not pdf_debug_logger.handlers:
    pdf_debug_handler = logging.FileHandler('pdf_debug.log', mode='w')
    pdf_debug_logger.addHandler(pdf_debug_handler)

def calculate_file_hash(file_path):
    """Calcula el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_all_pdf_files(directory):
    """Encuentra todos los archivos PDF en un directorio."""
    pdf_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, filename))
    return pdf_files

def is_file_processed(conn, file_hash):
    """Verifica si un archivo con un hash específico ya ha sido procesado."""
    cursor = conn.cursor(buffered=True)
    query = "SELECT 1 FROM raw_metadatos_cartolas_bancarias WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone() is not None
    return result

def get_source_id(conn, source_name='Banco de Chile - Línea de Crédito'):
    """Obtiene el ID de la fuente, creándolo si no existe."""
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
    """Inserta los metadatos del archivo PDF."""
    cursor = conn.cursor()
    query = '''
    INSERT INTO raw_metadatos_cartolas_bancarias (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    '''
    values = (source_id, os.path.basename(pdf_path), file_hash, 'Bank Statement - Credit Line')
    cursor.execute(query, values)
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte valores monetarios de string a float."""
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
    """Parsea un PDF de línea de crédito, separando datos crudos y procesados."""
    logging.info(f"Iniciando parseo con lógica de datos crudos/procesados para: {pdf_path}")
    processed_transactions = []
    raw_transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        hasta_date = None
        full_text_for_date = "".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        match = re.search(r"HASTA\s*:\s*(\d{2}/\d{2}/(\d{4}))", full_text_for_date)
        if match:
            hasta_date = datetime.strptime(match.group(1), "%d/%m/%Y")
        
        if not hasta_date:
            logging.error(f"La fecha 'HASTA' no pudo ser determinada para {pdf_path}.")
            return None

        hasta_year, hasta_month = hasta_date.year, hasta_date.month

        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, layout=True)
            if not text:
                continue

            in_transaction_block = False
            for line in text.split('\n'):
                if "SALDO INICIAL" in line:
                    in_transaction_block = True
                    continue
                if "SALDO FINAL" in line:
                    in_transaction_block = False
                    continue
                if not in_transaction_block or not line.strip():
                    continue
                if not re.match(r'^\d{2}/\d{2}', line.strip()):
                    continue

                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) < 2:
                    continue

                desc_part = parts[0]
                numbers_part = parts[-1]

                date_match = re.match(r'^(\d{2}/\d{2})\s+(.*)', desc_part)
                if not date_match:
                    continue
                
                date_str, desc_str = date_match.groups()
                desc_str = desc_str.strip()

                number_values = numbers_part.split()
                
                raw_cargo, raw_abono, raw_saldo = "", "", ""
                
                if len(number_values) == 1:
                    if "ABONO" in desc_str.upper():
                        raw_abono = number_values[0]
                    else:
                        raw_cargo = number_values[0]
                elif len(number_values) == 2:
                    raw_saldo = number_values[1]
                    if "ABONO" in desc_str.upper():
                        raw_abono = number_values[0]
                    else:
                        raw_cargo = number_values[0]
                elif len(number_values) == 3:
                    raw_cargo = number_values[0]
                    raw_abono = number_values[1]
                    raw_saldo = number_values[2]

                try:
                    tx_day, tx_month = map(int, date_str.split('/'))
                    correct_year = hasta_year
                    if tx_month > hasta_month and not (hasta_month == 1 and tx_month == 12):
                        correct_year -= 1
                    tx_date = pd.to_datetime(f"{tx_day}/{tx_month}/{correct_year}", format='%d/%m/%Y')
                except (ValueError, TypeError):
                    continue

                processed_transactions.append({
                    'fecha_transaccion': tx_date.strftime('%Y-%m-%d'),
                    'descripcion': desc_str,
                    'cargos': parse_and_clean_value(raw_cargo),
                    'abonos': parse_and_clean_value(raw_abono),
                    'saldo': parse_and_clean_value(raw_saldo)
                })
                raw_transactions.append({
                    'FECHA DIA/MES': date_str,
                    'DETALLE DE TRANSACCION': desc_str,
                    'MONTO CHEQUES O CARGOS': raw_cargo,
                    'MONTO DEPOSITOS O ABONOS': raw_abono,
                    'SALDO': raw_saldo
                })
    
    if not processed_transactions:
        logging.info(f"No se encontraron transacciones en el archivo: {pdf_path}")
        return pd.DataFrame(), pd.DataFrame(), 0, 0, 0

    processed_df = pd.DataFrame(processed_transactions)
    raw_df = pd.DataFrame(raw_transactions)

    expected_count = len(processed_df)
    expected_sum_cargos = processed_df['cargos'].sum()
    expected_sum_abonos = processed_df['abonos'].sum()

    return raw_df, processed_df, expected_count, expected_sum_cargos, expected_sum_abonos

def insert_raw_pdf_linea_credito_to_staging(conn, metadata_id, source_id, raw_df):
    """Inserta los datos crudos en la tabla de staging."""
    cursor = conn.cursor()
    cols = ", ".join([f'`{col}`' for col in raw_df.columns])
    placeholders = ", ".join(["%s"] * len(raw_df.columns))
    query = f"INSERT INTO staging_linea_credito_banco_chile_pdf (metadata_id, fuente_id, {cols}) VALUES (%s, %s, {placeholders})"
    
    rows_to_insert = [tuple([metadata_id, source_id] + list(row)) for row in raw_df.itertuples(index=False)]
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Se insertaron {len(rows_to_insert)} filas en staging para metadata_id: {metadata_id}")

def validate_staging_data(conn, metadata_id, expected_count, expected_sum_cargos, expected_sum_abonos):
    """Consulta y valida los datos en la tabla de staging."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM staging_linea_credito_banco_chile_pdf WHERE metadata_id = %s", (metadata_id,))
    actual_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(CAST(REPLACE(`MONTO CHEQUES O CARGOS`, '.', '') AS UNSIGNED)) FROM staging_linea_credito_banco_chile_pdf WHERE metadata_id = %s AND `MONTO CHEQUES O CARGOS` != ''", (metadata_id,))
    actual_sum_cargos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(CAST(REPLACE(`MONTO DEPOSITOS O ABONOS`, '.', '') AS UNSIGNED)) FROM staging_linea_credito_banco_chile_pdf WHERE metadata_id = %s AND `MONTO DEPOSITOS O ABONOS` != ''", (metadata_id,))
    actual_sum_abonos = cursor.fetchone()[0] or 0.0
    
    count_valid = actual_count == expected_count
    sum_cargos_valid = abs(float(actual_sum_cargos) - expected_sum_cargos) < 0.01
    sum_abonos_valid = abs(float(actual_sum_abonos) - expected_sum_abonos) < 0.01

    logging.info(f"VALIDACIÓN CONTEO: ESPERADO={expected_count}, OBTENIDO={actual_count}")
    logging.info(f"VALIDACIÓN SUMA CARGOS: ESPERADO={expected_sum_cargos}, OBTENIDO={float(actual_sum_cargos)}")
    logging.info(f"VALIDACIÓN SUMA ABONOS: ESPERADO={expected_sum_abonos}, OBTENIDO={float(actual_sum_abonos)}")

    return count_valid and sum_cargos_valid and sum_abonos_valid

def insert_linea_credito_transactions(conn, metadata_id, source_id, transactions_df):
    """Inserta las transacciones de línea de crédito procesadas en la tabla raw."""
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_transacciones_linea_credito (
        metadata_id, fuente_id, fecha_transaccion, descripcion, cargos, abonos
    ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in transactions_df.iterrows():
        rows_to_insert.append((
            metadata_id,
            source_id,
            row.get('fecha_transaccion'),
            row.get('descripcion'),
            row.get('cargos'),
            row.get('abonos')
        ))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones en raw_transacciones_linea_credito para metadata_id: {metadata_id}")

def move_file_to_processed(pdf_path, file_hash):
    """Mueve un archivo a la carpeta de procesados con un nombre estandarizado."""
    processed_dir = os.path.join(os.path.dirname(pdf_path), 'procesados')
    os.makedirs(processed_dir, exist_ok=True)
    short_hash = file_hash[:8]
    new_filename = f"LC_BChile_{{datetime.now().strftime('%Y%m%d')}}_{short_hash}.pdf"
    processed_filepath = os.path.join(processed_dir, new_filename)
    shutil.move(pdf_path, processed_filepath)
    logging.info(f"Archivo movido a {processed_filepath}")
    log_file_movement(pdf_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")

def main():
    """Función principal para orquestar el procesamiento de archivos PDF."""
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
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado, omitiendo: {os.path.basename(pdf_path)}")
                    continue

                result = parse_linea_credito_pdf(pdf_path)
                if result is None:
                    ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Failed - Critical parsing error")
                    continue

                raw_df, processed_df, count, sum_cargos, sum_abonos = result

                if processed_df.empty:
                    logging.info(f"No se encontraron transacciones en {os.path.basename(pdf_path)}. Moviendo archivo.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Processed - No transactions found")
                    move_file_to_processed(pdf_path, file_hash)
                    continue

                # La transacción comienza implícitamente con la primera inserción
                metadata_id = insert_metadata(conn, source_id, pdf_path, file_hash)
                insert_raw_pdf_linea_credito_to_staging(conn, metadata_id, source_id, raw_df)

                if not validate_staging_data(conn, metadata_id, count, sum_cargos, sum_abonos):
                    logging.error(f"La validación de staging falló para {os.path.basename(pdf_path)}. Revirtiendo.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Failed - Staging validation failed")
                    conn.rollback()
                    continue
                
                # Transferir de staging a raw
                insert_linea_credito_transactions(conn, metadata_id, source_id, processed_df)

                conn.commit()
                ingestion_status_logger.info(f"FILE: {os.path.basename(pdf_path)} | HASH: {file_hash} | STATUS: Processed Successfully")
                move_file_to_processed(pdf_path, file_hash)

            except Exception as e:
                logging.error(f"Error procesando {os.path.basename(pdf_path)}: {e}", exc_info=True)
                if conn.in_transaction:
                    conn.rollback()

if __name__ == '__main__':
    main()
