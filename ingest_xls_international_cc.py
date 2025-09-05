import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement, generate_standardized_filename
from database_utils import db_connection
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN ---
DOCUMENT_TYPE = 'TC_INTERNACIONAL_BCH'

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración del logger para el estado de la ingesta
ingestion_status_logger = logging.getLogger('ingestion_status')
ingestion_status_logger.setLevel(logging.INFO)
if not ingestion_status_logger.handlers:
    status_file_handler = logging.FileHandler('ingestion_status.log')
    status_formatter = logging.Formatter('%(asctime)s - %(message)s')
    status_file_handler.setFormatter(status_formatter)
    ingestion_status_logger.addHandler(status_file_handler)

def calculate_file_hash(file_path):
    """Calcula el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_all_xls_files(directory):
    """Encuentra todos los archivos XLS/XLSX en un directorio."""
    xls_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.xls', '.xlsx')):
            xls_files.append(os.path.join(directory, filename))
    return xls_files

def is_file_processed(conn, file_hash):
    """Verifica si un archivo con un hash específico ya ha sido procesado."""
    cursor = conn.cursor(buffered=True)
    query = "SELECT 1 FROM raw_metadatos_cartolas_bancarias WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone() is not None
    return result

def get_source_id(conn, source_name):
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
        return cursor.lastrowid

def insert_metadata(conn, source_id, file_path, file_hash, doc_type_desc):
    """Inserta los metadatos del archivo, incluyendo su hash y tipo de documento."""
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_metadatos_cartolas_bancarias (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type_desc)
    cursor.execute(query, values)
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte valores monetarios."""
    if value is None:
        return 0.0
    if isinstance(value, str):
        if ',' in value:
            value = value.replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if pd.notna(value) else 0.0

def parse_and_clean_usd_value(value):
    """Limpia y convierte valores monetarios en USD."""
    if value is None:
        return 0.0
    if isinstance(value, str):
        value = value.replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if pd.notna(value) else 0.0

def load_abono_mappings(conn):
    """Carga las descripciones de abono desde la tabla abonos_mapping."""
    abono_descriptions = set()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT description FROM abonos_mapping")
            rows = cursor.fetchall()
            for row in rows:
                abono_descriptions.add(row['description'].strip())
        logging.info(f"Cargadas {len(abono_descriptions)} descripciones de abono.")
    except Exception as e:
        logging.error(f"Error al cargar mapeos de abonos: {e}")
    return abono_descriptions

def process_international_cc_xls_file(xls_path, abono_descriptions):
    """Procesa un XLS internacional y retorna DFs, métricas y el período del documento."""
    logging.info(f"Iniciando procesamiento de XLS internacional: {xls_path}")
    try:
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=50)
        
        keywords_required = ["Fecha", "Descripción"]
        keywords_optional = ["Monto", "Cargo", "Abono", "Importe"]
        header_row_index = -1

        for index in range(17, len(df_initial_read)):
            row = df_initial_read.iloc[index]
            row_str = row.astype(str).str.cat(sep=' ')
            
            if all(keyword in row_str for keyword in keywords_required) and \
               any(keyword in row_str for keyword in keywords_optional):
                header_row_index = index
                break
        
        if header_row_index == -1:
            logging.error(f"No se encontró la fila de cabecera de transacciones en {os.path.basename(xls_path)}.")
            return None, None, 0, 0, 0, 0, None

        df_transactions = pd.read_excel(xls_path, skiprows=header_row_index, header=0)
        df_transactions.dropna(subset=['Fecha'], inplace=True)

        if 'Monto ($)' in df_transactions.columns:
            df_transactions.rename(columns={'Monto ($)': 'Monto (USD)'}, inplace=True)
        
        if 'Monto Moneda Origen' not in df_transactions.columns and 'Monto' in df_transactions.columns:
            df_transactions.rename(columns={'Monto': 'Monto Moneda Origen'}, inplace=True)

        columns_to_keep_raw = [col for col in df_transactions.columns if not col.startswith('Unnamed')]
        raw_df = df_transactions[columns_to_keep_raw].copy()
        raw_df = raw_df.astype(object).where(pd.notnull(raw_df), None)

        column_mapping = {
            'Fecha': 'fecha_cargo_original',
            'Descripción': 'descripcion_transaccion',
            'Categoría': 'categoria',
            'Cuotas': 'cuotas_raw',
            'Monto Moneda Origen': 'monto_bruto',
            'Monto (USD)': 'monto_usd',
            'País': 'pais'
        }
        df_transactions.rename(columns=column_mapping, inplace=True)

        columns_to_keep = [col for col in column_mapping.values() if col in df_transactions.columns]
        df_transactions = df_transactions[columns_to_keep]

        if 'cuotas_raw' in df_transactions.columns:
            df_transactions['cuota_actual'] = df_transactions['cuotas_raw'].astype(str).apply(lambda x: int(x.split('/')[0]) if '/' in x else 1)
            df_transactions['total_cuotas'] = df_transactions['cuotas_raw'].astype(str).apply(lambda x: int(x.split('/')[1]) if '/' in x else 1)
        else:
            df_transactions['cuota_actual'] = 1
            df_transactions['total_cuotas'] = 1

        df_transactions['fecha_cargo_original'] = pd.to_datetime(df_transactions['fecha_cargo_original'], errors='coerce')
        
        df_transactions['fecha_cargo_cuota'] = df_transactions.apply(
            lambda row: row['fecha_cargo_original'] + relativedelta(months=row['cuota_actual'] - 1)
            if pd.notna(row['fecha_cargo_original']) and row['cuota_actual'] >= 1
            else row['fecha_cargo_original'] if pd.notna(row['fecha_cargo_original']) else pd.NaT,
            axis=1
        )

        document_period = df_transactions['fecha_cargo_cuota'].max()
        if pd.isna(document_period):
            document_period = df_transactions['fecha_cargo_original'].max()

        df_transactions['fecha_cargo_original'] = df_transactions['fecha_cargo_original'].dt.strftime('%Y-%m-%d')
        df_transactions['fecha_cargo_cuota'] = df_transactions['fecha_cargo_cuota'].dt.strftime('%Y-%m-%d')

        df_transactions['cargos_pesos'] = 0.0
        df_transactions['abonos_pesos'] = 0.0

        for index, row in df_transactions.iterrows():
            monto = parse_and_clean_value(row.get('monto_bruto'))
            description = str(row.get('descripcion_transaccion', '')).strip()
            
            if description in abono_descriptions:
                df_transactions.loc[index, 'abonos_pesos'] = monto
            else:
                df_transactions.loc[index, 'cargos_pesos'] = monto

        if 'monto_usd' not in df_transactions.columns:
            df_transactions['monto_usd'] = 0.0
        df_transactions['monto_usd'] = df_transactions['monto_usd'].apply(parse_and_clean_usd_value)
        
        df_transactions['tipo_cambio'] = df_transactions.apply(
            lambda row: row['cargos_pesos'] / row['monto_usd'] if row['monto_usd'] != 0 else 0.0,
            axis=1
        )
        
        if 'pais' not in df_transactions.columns:
            df_transactions['pais'] = None

        df_transactions = df_transactions.astype(object).where(pd.notnull(df_transactions), None)

        expected_count = len(df_transactions)
        expected_sum_cargos = df_transactions['cargos_pesos'].sum()
        expected_sum_abonos = df_transactions['abonos_pesos'].sum()
        expected_sum_usd = df_transactions['monto_usd'].sum()

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {expected_count} transacciones. Período: {document_period.strftime('%Y-%m') if document_period else 'N/A'}")
        return raw_df, df_transactions, expected_count, expected_sum_cargos, expected_sum_abonos, expected_sum_usd, document_period

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None, None, 0, 0, 0, 0, None

def insert_credit_card_transactions(conn, metadata_id, source_id, transactions_df):
    """Inserta las transacciones de tarjeta de crédito procesadas en la base de datos."""
    transactions_df = transactions_df.where(pd.notnull(transactions_df), None)
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_transacciones_tarjeta_credito_internacional (
        metadata_id, fuente_id, fecha_cargo_original, fecha_cargo_cuota, descripcion_transaccion, 
        categoria, cuota_actual, total_cuotas, cargos_pesos, abonos_pesos, monto_usd, tipo_cambio, pais
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in transactions_df.iterrows():
        rows_to_insert.append((
            metadata_id, source_id,
            row.get('fecha_cargo_original'), row.get('fecha_cargo_cuota'),
            row.get('descripcion_transaccion'), row.get('categoria'),
            row.get('cuota_actual'), row.get('total_cuotas'),
            row.get('cargos_pesos'), row.get('abonos_pesos'),
            row.get('monto_usd'), row.get('tipo_cambio'),
            row.get('pais')
        ))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones de tarjeta de crédito para metadata_id: {metadata_id}")

def insert_raw_international_cc_to_staging(conn, metadata_id, source_id, raw_df):
    """Inserta los datos crudos de la cartola de Tarjeta de Crédito Internacional en la tabla de staging."""
    cursor = conn.cursor()
    cols = ", ".join([f'`{col}`' for col in raw_df.columns])
    placeholders = ", ".join(["%s"] * len(raw_df.columns))
    query = f"""
    INSERT INTO staging_tarjeta_credito_banco_de_chile_internacional (metadata_id, fuente_id, {cols})
    VALUES (%s, %s, {placeholders})
    """
    
    rows_to_insert = []
    for _, row in raw_df.iterrows():
        values = [metadata_id, source_id] + row.tolist()
        rows_to_insert.append(tuple(values))

    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Se insertaron {len(rows_to_insert)} filas en staging_tarjeta_credito_banco_de_chile_internacional para metadata_id: {metadata_id}")

def validate_staging_data(conn, metadata_id, expected_count, expected_sum_cargos, expected_sum_abonos, expected_sum_usd, abono_descriptions):
    """Consulta la tabla de staging y valida el conteo y la suma de los montos."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM staging_tarjeta_credito_banco_de_chile_internacional WHERE metadata_id = %s", (metadata_id,))
        rows = cursor.fetchall()
        actual_count = len(rows)

        actual_sum_cargos = 0
        actual_sum_abonos = 0
        actual_sum_usd = 0

        for row in rows:
            description = str(row.get('Descripción', '')).strip()
            monto_origen = parse_and_clean_value(row.get('Monto Moneda Origen'))
            monto_usd = parse_and_clean_usd_value(row.get('Monto (USD)'))

            if description in abono_descriptions:
                actual_sum_abonos += monto_origen
            else:
                actual_sum_cargos += monto_origen
            actual_sum_usd += monto_usd

        count_valid = actual_count == expected_count
        sum_cargos_valid = abs(actual_sum_cargos - expected_sum_cargos) < 0.01
        sum_abonos_valid = abs(actual_sum_abonos - expected_sum_abonos) < 0.01
        sum_usd_valid = abs(actual_sum_usd - expected_sum_usd) < 0.01

        logging.info(f"VALIDACIÓN CONTEO: {'ÉXITO' if count_valid else 'FALLO'} ({actual_count}/{expected_count})")
        # ... (rest of validation logging)

        return count_valid and sum_cargos_valid and sum_abonos_valid and sum_usd_valid
            
    except Exception as e:
        logging.error(f"Ocurrió un error durante la validación de staging: {e}", exc_info=True)
        return False
    finally:
        cursor.close()

def main():
    """Función principal para orquestar el procesamiento de archivos XLS."""
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\tarjeta de credito\internacional'
    source_name = 'Banco de Chile - Tarjeta Credito Internacional'
    doc_type_desc = 'International Credit Card Statement'

    xls_files = find_all_xls_files(xls_directory)

    if not xls_files:
        logging.info(f"No se encontraron archivos XLS/XLSX en: {xls_directory}")
        return

    logging.info(f"Se encontraron {len(xls_files)} archivos XLS/XLSX para procesar.")

    with db_connection() as conn:
        abono_descriptions = load_abono_mappings(conn)
        source_id = get_source_id(conn, source_name)
        for xls_path in xls_files:
            file_hash = None
            try:
                file_hash = calculate_file_hash(xls_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado, omitiendo: {os.path.basename(xls_path)}")
                    continue

                result = process_international_cc_xls_file(xls_path, abono_descriptions)
                
                if result is None or result[1] is None or result[1].empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Parsing failed or no data")
                    conn.rollback()
                    continue
                
                raw_df, processed_df, expected_count, expected_sum_cargos, expected_sum_abonos, expected_sum_usd, document_period = result

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, doc_type_desc)
                insert_raw_international_cc_to_staging(conn, metadata_id, source_id, raw_df)

                if not validate_staging_data(conn, metadata_id, expected_count, expected_sum_cargos, expected_sum_abonos, expected_sum_usd, abono_descriptions):
                    logging.error(f"La validación de datos de staging falló para {os.path.basename(xls_path)}. Revirtiendo.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Staging validation failed")
                    conn.rollback()
                    continue

                insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                
                conn.commit()

                # Mover y renombrar archivo procesado
                processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
                os.makedirs(processed_dir, exist_ok=True)
                new_filename = generate_standardized_filename(
                    document_type=DOCUMENT_TYPE,
                    document_period=document_period,
                    file_hash=file_hash,
                    original_filename=os.path.basename(xls_path)
                )
                processed_filepath = os.path.join(processed_dir, new_filename)
                shutil.move(xls_path, processed_filepath)
                log_file_movement(xls_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")

                logging.info(f"Proceso de ingesta completado con éxito para: {os.path.basename(xls_path)}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Processed Successfully")

            except Exception as e:
                logging.error(f"Ocurrió un error CRÍTICO procesando el archivo {os.path.basename(xls_path)}: {e}", exc_info=True)
                if conn.in_transaction:
                    conn.rollback()
                log_file_movement(xls_path, "N/A", "FAILED", f"Error al procesar: {e}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash or 'N/A'} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()