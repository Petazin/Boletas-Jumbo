import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement, generate_standardized_filename
from database_utils import db_connection
from datetime import datetime

# --- CONFIGURACIÓN ---
DOCUMENT_TYPE = 'TC_FALABELLA'

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def find_all_xls_files(directory):
    xls_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.xls', '.xlsx')):
            xls_files.append(os.path.join(directory, filename))
    return xls_files

def is_file_processed(conn, file_hash):
    cursor = conn.cursor(buffered=True)
    query = "SELECT 1 FROM raw_metadatos_documentos WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    return cursor.fetchone() is not None

def get_source_id(conn, source_name):
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

def insert_metadata(conn, source_id, file_path, file_hash, doc_type_desc):
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_metadatos_documentos (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type_desc)
    cursor.execute(query, values)
    return cursor.lastrowid

def parse_and_clean_value(value):
    if isinstance(value, str):
        value = value.replace('$', '').replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if pd.notna(value) else 0.0

def process_falabella_cc_xls(xls_path):
    logging.info(f"Iniciando procesamiento de XLS de Banco Falabella: {os.path.basename(xls_path)}")
    try:
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=20)
        header_row_index = -1
        for i, row in df_initial_read.iterrows():
            if 'FECHA' in row.to_string() and 'DESCRIPCION' in row.to_string():
                header_row_index = i
                break
        
        if header_row_index == -1:
            logging.error(f"No se encontró la fila de cabecera de transacciones en {os.path.basename(xls_path)}.")
            return None, None, 0, 0, None

        df = pd.read_excel(xls_path, skiprows=header_row_index)
        df.dropna(how='all', inplace=True)
        df = df[df['FECHA'].notna()]
        df = df.astype(object).where(pd.notnull(df), None)

        raw_df = df.copy()

        processed_df = df.rename(columns={
            'FECHA': 'fecha_cargo_original',
            'DESCRIPCION': 'descripcion_transaccion',
            'VALOR CUOTA': 'cargos_pesos',
            'CUOTAS PENDIENTES': 'cuotas_raw'
        })

        processed_df['fecha_cargo_original'] = pd.to_datetime(processed_df['fecha_cargo_original'], format='%d-%m-%Y', errors='coerce')
        processed_df['fecha_cargo_cuota'] = processed_df['fecha_cargo_original']
        processed_df['cargos_pesos'] = processed_df['cargos_pesos'].apply(parse_and_clean_value)
        processed_df['abonos_pesos'] = 0.0

        cuotas_raw = processed_df.get('cuotas_raw')
        if cuotas_raw is not None:
            cuotas_split = cuotas_raw.astype(str).str.split('/', expand=True)
            processed_df['cuota_actual'] = pd.to_numeric(cuotas_split[0], errors='coerce').fillna(1).astype(int)
            if 1 in cuotas_split.columns:
                processed_df['total_cuotas'] = pd.to_numeric(cuotas_split[1], errors='coerce').fillna(1).astype(int)
            else:
                processed_df['total_cuotas'] = 1
        else:
            processed_df['cuota_actual'] = 1
            processed_df['total_cuotas'] = 1

        document_period = processed_df['fecha_cargo_original'].max()

        expected_count = len(processed_df)
        expected_sum = processed_df['cargos_pesos'].sum()

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {expected_count} transacciones. Período: {document_period.strftime('%Y-%m') if document_period else 'N/A'}")
        return raw_df, processed_df, expected_count, expected_sum, document_period

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None, None, 0, 0, None

def insert_credit_card_transactions(conn, metadata_id, source_id, transactions_df):
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_transacciones_tarjeta_credito_nacional (
        metadata_id, fuente_id, fecha_cargo_original, fecha_cargo_cuota, descripcion_transaccion, 
        cuota_actual, total_cuotas, cargos_pesos, abonos_pesos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in transactions_df.iterrows():
        rows_to_insert.append((
            metadata_id, source_id,
            row.get('fecha_cargo_original').strftime('%Y-%m-%d') if pd.notna(row.get('fecha_cargo_original')) else None,
            row.get('fecha_cargo_cuota').strftime('%Y-%m-%d') if pd.notna(row.get('fecha_cargo_cuota')) else None,
            row.get('descripcion_transaccion'),
            row.get('cuota_actual'),
            row.get('total_cuotas'),
            row.get('cargos_pesos'),
            row.get('abonos_pesos')
        ))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones para metadata_id: {metadata_id}")

def insert_raw_falabella_cc_to_staging(conn, metadata_id, source_id, raw_df):
    cursor = conn.cursor()
    staging_columns = ['FECHA', 'DESCRIPCION', 'VALOR CUOTA', 'CUOTAS PENDIENTES']
    raw_df_staging = raw_df[[col for col in staging_columns if col in raw_df.columns]]

    cols = ", ".join([f'`{col}`' for col in raw_df_staging.columns])
    placeholders = ", ".join(["%s"] * len(raw_df_staging.columns))
    query = f"INSERT INTO staging_tarjeta_credito_falabella_nacional (metadata_id, fuente_id, {cols}) VALUES (%s, %s, {placeholders})"
    
    rows_to_insert = [tuple([metadata_id, source_id] + [None if pd.isna(val) else val for val in row]) for row in raw_df_staging.itertuples(index=False)]
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Se insertaron {len(rows_to_insert)} filas en staging_tarjeta_credito_falabella_nacional para metadata_id: {metadata_id}")

def validate_staging_data(conn, metadata_id, expected_count, expected_sum):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM staging_tarjeta_credito_falabella_nacional WHERE metadata_id = %s", (metadata_id,))
        actual_count = cursor.fetchone()[0]

        query_sum = "SELECT SUM(CAST(REPLACE(REPLACE(`VALOR CUOTA`, '$', ''), '.', '') AS DECIMAL(15,2))) FROM staging_tarjeta_credito_falabella_nacional WHERE metadata_id = %s"
        cursor.execute(query_sum, (metadata_id,))
        actual_sum_result = cursor.fetchone()[0]
        actual_sum = float(actual_sum_result) if actual_sum_result is not None else 0.0
        
        count_valid = actual_count == expected_count
        sum_valid = abs(actual_sum - expected_sum) < 0.01

        logging.info(f"VALIDACIÓN CONTEO: {'ÉXITO' if count_valid else 'FALLO'} ({actual_count}/{expected_count})")
        logging.info(f"VALIDACIÓN SUMA: {'ÉXITO' if sum_valid else 'FALLO'} ({actual_sum}/{expected_sum})")
        return count_valid and sum_valid
    except Exception as e:
        logging.error(f"Ocurrió un error durante la validación de staging: {e}", exc_info=True)
        return False
    finally:
        cursor.close()

def move_file_to_processed(xls_path, file_hash, document_type, document_period):
    """Mueve un archivo a la carpeta de procesados con un nombre estandarizado."""
    processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
    os.makedirs(processed_dir, exist_ok=True)
    
    new_filename = generate_standardized_filename(
        document_type=document_type,
        document_period=document_period,
        file_hash=file_hash,
        original_filename=os.path.basename(xls_path)
    )
    
    processed_filepath = os.path.join(processed_dir, new_filename)
    shutil.move(xls_path, processed_filepath)
    logging.info(f"Archivo movido a {processed_filepath}")
    log_file_movement(xls_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")

def main():
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\Banco falabella\tarjeta de credito\nacional'
    source_name = 'Banco Falabella - Tarjeta Credito'
    doc_type_desc = 'Credit Card Statement'

    xls_files = find_all_xls_files(xls_directory)
    if not xls_files:
        logging.info(f"No se encontraron archivos XLS/XLSX en: {xls_directory}")
        return

    logging.info(f"Se encontraron {len(xls_files)} archivos XLS/XLSX para procesar.")

    with db_connection() as conn:
        source_id = get_source_id(conn, source_name)
        for xls_path in xls_files:
            file_hash = None
            try:
                file_hash = calculate_file_hash(xls_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado, omitiendo: {os.path.basename(xls_path)}")
                    continue

                result = process_falabella_cc_xls(xls_path)
                if result is None:
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Critical parsing error")
                    continue
                
                raw_df, processed_df, expected_count, expected_sum, document_period = result
                if processed_df is None or processed_df.empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - No data parsed")
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, doc_type_desc)
                insert_raw_falabella_cc_to_staging(conn, metadata_id, source_id, raw_df)

                if not validate_staging_data(conn, metadata_id, expected_count, expected_sum):
                    logging.error(f"La validación de staging falló para {os.path.basename(xls_path)}. Revirtiendo.")
                    conn.rollback()
                    continue

                insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                conn.commit()

                move_file_to_processed(xls_path, file_hash, DOCUMENT_TYPE, document_period)
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Processed Successfully")

            except Exception as e:
                logging.error(f"Ocurrió un error CRÍTICO procesando el archivo {os.path.basename(xls_path)}: {e}", exc_info=True)
                if conn.in_transaction:
                    conn.rollback()
                log_file_movement(xls_path, "N/A", "FAILED", f"Error al procesar: {e}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash or 'N/A'} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()