import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement
from database_utils import db_connection
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta


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
    # No cerrar el cursor aquí para reutilizar la conexión
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
        # No hacer commit aquí, se manejará de forma transaccional
        return cursor.lastrowid

def insert_metadata(conn, source_id, file_path, file_hash, doc_type):
    """Inserta los metadatos del archivo, incluyendo su hash y tipo de documento."""
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_metadatos_cartolas_bancarias (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type)
    cursor.execute(query, values)
    # No hacer commit aquí
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte valores monetarios, manejando el símbolo '.'"""
    if isinstance(value, str):
        value = value.replace('$', '').replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if value is not None else 0.0

def process_falabella_cc_xls_file(xls_path):
    """
    Procesa un archivo XLS de cartola de tarjeta de crédito de Banco Falabella.
    """
    logging.info(f"Iniciando procesamiento de XLS de Banco Falabella: {xls_path}")
    try:
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=50)
        
        keywords_required = ["FECHA", "DESCRIPCION", "MONTO"]
        keywords_optional = ["CUOTAS PENDIENTES", "VALOR CUOTA"]
        header_row_index = -1

        for index in range(len(df_initial_read)):
            row = df_initial_read.iloc[index]
            row_str = row.astype(str).str.cat(sep=' ')
            
            if all(keyword in row_str for keyword in keywords_required) and \
               any(keyword in row_str for keyword in keywords_optional):
                header_row_index = index
                break
        
        if header_row_index == -1:
            logging.error(f"No se encontró la fila de cabecera de transacciones en {os.path.basename(xls_path)}.")
            return None

        df_transactions = pd.read_excel(xls_path, skiprows=header_row_index, header=0) 
        raw_df = df_transactions.copy()
        
        column_mapping = {
            'FECHA': 'fecha_cargo_original',
            'DESCRIPCION': 'descripcion_transaccion',
            'VALOR CUOTA': 'cargos_pesos',
            'CUOTAS PENDIENTES': 'cuotas_raw'
        }
        df_transactions.rename(columns=column_mapping, inplace=True)

        columns_to_keep = ['fecha_cargo_original', 'descripcion_transaccion', 'cargos_pesos', 'cuotas_raw']
        df_transactions = df_transactions[[col for col in columns_to_keep if col in df_transactions.columns]]

        df_transactions['cuota_actual'] = 1
        df_transactions['total_cuotas'] = 1

        df_transactions['fecha_cargo_original'] = pd.to_datetime(df_transactions['fecha_cargo_original'], format='%d-%m-%Y', errors='coerce')
        df_transactions['fecha_cargo_cuota'] = df_transactions['fecha_cargo_original']

        df_transactions['fecha_cargo_original'] = df_transactions['fecha_cargo_original'].dt.strftime('%Y-%m-%d')
        df_transactions['fecha_cargo_cuota'] = df_transactions['fecha_cargo_cuota'].dt.strftime('%Y-%m-%d')

        df_transactions['cargos_pesos'] = df_transactions['cargos_pesos'].apply(parse_and_clean_value)
        
        df_transactions.dropna(subset=['fecha_cargo_original'], inplace=True)

        expected_count = len(df_transactions)
        expected_sum = df_transactions['cargos_pesos'].sum()

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {expected_count} transacciones listas. Suma esperada: {expected_sum}")
        
        return raw_df, df_transactions, expected_count, expected_sum

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None

def insert_credit_card_transactions(conn, metadata_id, source_id, transactions_df):
    """
    Inserta las transacciones de tarjeta de crédito procesadas en la base de datos.
    """
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_transacciones_tarjeta_credito (
        metadata_id, fuente_id, fecha_cargo_original, fecha_cargo_cuota, descripcion_transaccion, 
        categoria, cuota_actual, total_cuotas, cargos_pesos, monto_usd, tipo_cambio, pais
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in transactions_df.iterrows():
        rows_to_insert.append((
            metadata_id, source_id,
            row.get('fecha_cargo_original'), row.get('fecha_cargo_cuota'),
            row.get('descripcion_transaccion'), row.get('categoria', None),
            row.get('cuota_actual'), row.get('total_cuotas'),
            row.get('cargos_pesos'), row.get('monto_usd', None),
            row.get('tipo_cambio', None), row.get('pais', None)
        ))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones para metadata_id: {metadata_id}")

def insert_raw_falabella_cc_to_staging(conn, metadata_id, source_id, raw_df):
    """Inserta los datos crudos de la cartola de Tarjeta de Crédito Falabella en la tabla de staging."""
    cursor = conn.cursor()
    
    staging_columns = ['FECHA', 'DESCRIPCION', 'VALOR CUOTA', 'CUOTAS PENDIENTES']
    raw_df_staging = raw_df[staging_columns]

    cols = ", ".join([f'`{col}`' for col in raw_df_staging.columns])
    placeholders = ", ".join(["%s"] * len(raw_df_staging.columns))
    query = f"""
    INSERT INTO staging_tarjeta_credito_falabella_nacional (metadata_id, fuente_id, {cols})
    VALUES (%s, %s, {placeholders})
    """
    
    rows_to_insert = []
    for _, row in raw_df_staging.iterrows():
        values = [metadata_id, source_id] + [None if pd.isna(val) else val for val in row.tolist()]
        rows_to_insert.append(tuple(values))

    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Se insertaron {len(rows_to_insert)} filas en staging_tarjeta_credito_falabella_nacional para metadata_id: {metadata_id}")

def validate_staging_data(conn, metadata_id, expected_count, expected_sum):
    """Consulta la tabla de staging y valida el conteo y la suma de los montos."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM staging_tarjeta_credito_falabella_nacional WHERE metadata_id = %s", (metadata_id,))
        actual_count = cursor.fetchone()[0]

        query_sum = """
        SELECT SUM(CAST(REPLACE(REPLACE(`VALOR CUOTA`, '$', ''), '.', '') AS DECIMAL(15,2)))
        FROM staging_tarjeta_credito_falabella_nacional
        WHERE metadata_id = %s
        """
        cursor.execute(query_sum, (metadata_id,))
        actual_sum_result = cursor.fetchone()[0]
        actual_sum = float(actual_sum_result) if actual_sum_result is not None else 0.0
        
        count_valid = actual_count == expected_count
        sum_valid = abs(actual_sum - expected_sum) < 0.01

        if count_valid:
            logging.info(f"VALIDACIÓN CONTEO: ÉXITO ({actual_count}/{expected_count})")
        else:
            logging.error(f"VALIDACIÓN CONTEO: FALLO ({actual_count}/{expected_count})")

        if sum_valid:
            logging.info(f"VALIDACIÓN SUMA: ÉXITO ({actual_sum}/{expected_sum})")
        else:
            logging.error(f"VALIDACIÓN SUMA: FALLO ({actual_sum}/{expected_sum})")
        
        return count_valid and sum_valid
            
    except Exception as e:
        logging.error(f"Ocurrió un error durante la validación de staging: {e}", exc_info=True)
        return False
    finally:
        cursor.close()

def main():
    """
    Función principal para orquestar el procesamiento de archivos XLS de Banco Falabella.
    """
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\Banco falabella\tarjeta de credito\nacional'
    source_name = 'Banco Falabella - Tarjeta Credito'
    document_type = 'Credit Card Statement'

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
                # conn.start_transaction() # Comentado para evitar error
                file_hash = calculate_file_hash(xls_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado (hash existente), omitiendo: {os.path.basename(xls_path)}")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Skipped - Already Processed")
                    conn.rollback()
                    continue

                result = process_falabella_cc_xls_file(xls_path)
                
                if result is None:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Parsing failed")
                    conn.rollback()
                    continue
                
                raw_df, processed_df, expected_count, expected_sum = result
                
                if processed_df is None or processed_df.empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - No data parsed")
                    conn.rollback()
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                insert_raw_falabella_cc_to_staging(conn, metadata_id, source_id, raw_df)
                
                if not validate_staging_data(conn, metadata_id, expected_count, expected_sum):
                    logging.error(f"La validación de datos de staging falló para {os.path.basename(xls_path)}. Revirtiendo cambios.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Staging validation failed")
                    conn.rollback()
                    continue

                insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                
                conn.commit()

                processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
                os.makedirs(processed_dir, exist_ok=True)
                processed_filepath = os.path.join(processed_dir, os.path.basename(xls_path))
                shutil.move(xls_path, processed_filepath)
                logging.info(f"Archivo movido a la carpeta de procesados: {processed_filepath}")
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