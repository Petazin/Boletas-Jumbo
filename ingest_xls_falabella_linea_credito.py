import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement
from database_utils import db_connection
from datetime import datetime


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

def insert_metadata(conn, source_id, file_path, file_hash, doc_type):
    """Inserta los metadatos del archivo en la tabla común de metadatos."""
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_metadatos_cartolas_bancarias (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type)
    cursor.execute(query, values)
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte valores monetarios o de tasas."""
    if isinstance(value, str):
        cleaned_value = value.replace('$', '').replace('.', '').replace(',', '.')
        cleaned_value = cleaned_value.replace('%', '').strip()
        try:
            return float(cleaned_value) if cleaned_value and cleaned_value != '-' else 0.0
        except ValueError:
            return 0.0
    return value if pd.notna(value) else 0.0

def process_falabella_linea_credito_xls_file(xls_path):
    """
    Procesa un archivo XLS de cartola de Línea de Crédito de Banco Falabella.
    """
    logging.info(f"Iniciando procesamiento de XLS de Línea de Crédito: {os.path.basename(xls_path)}")
    try:
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=20)
        
        keywords_required = ["Fecha", "Descripcion", "Cargos", "Abonos", "Monto utilizado"]
        header_row_index = -1

        for index in range(len(df_initial_read)):
            row_str = ' '.join(map(str, df_initial_read.iloc[index].dropna())).lower()
            if all(keyword.lower() in row_str for keyword in keywords_required):
                header_row_index = index
                break
        
        if header_row_index == -1:
            logging.error(f"No se encontró la fila de cabecera de transacciones en {os.path.basename(xls_path)}.")
            return None

        df = pd.read_excel(xls_path, skiprows=header_row_index)
        raw_df = df.copy()
        
        df.columns = df.columns.str.strip()

        column_mapping = {
            'Fecha': 'fecha_transaccion', 'Descripcion': 'descripcion', 'Cargos': 'cargos',
            'Abonos': 'abonos', 'Monto utilizado': 'monto_utilizado',
            'Tasa diaria': 'tasa_diaria', 'Intereses': 'intereses'
        }
        df.rename(columns=column_mapping, inplace=True)
        df.dropna(subset=['fecha_transaccion'], inplace=True)
        df['fecha_transaccion'] = pd.to_datetime(df['fecha_transaccion'], errors='coerce').dt.date

        for col in ['cargos', 'abonos', 'monto_utilizado', 'tasa_diaria', 'intereses']:
            if col in df.columns:
                df[col] = df[col].apply(parse_and_clean_value)
        
        df = df.astype(object).where(pd.notnull(df), None)

        expected_count = len(df)
        expected_sum_cargos = df['cargos'].sum()
        expected_sum_abonos = df['abonos'].sum()

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {expected_count} transacciones listas.")
        return raw_df, df, expected_count, expected_sum_cargos, expected_sum_abonos

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None

def insert_linea_credito_transactions(conn, metadata_id, source_id, df):
    """
    Inserta las transacciones de línea de crédito en la nueva tabla.
    """
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_transacciones_linea_credito (
        metadata_id, fuente_id, fecha_transaccion, descripcion, cargos, abonos,
        monto_utilizado, tasa_diaria, intereses, linea_original_datos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in df.iterrows():
        original_line = ', '.join(map(str, row.values))
        rows_to_insert.append((
            metadata_id, source_id, row.get('fecha_transaccion'), row.get('descripcion'),
            row.get('cargos'), row.get('abonos'), row.get('monto_utilizado'),
            row.get('tasa_diaria'), row.get('intereses'), original_line
        ))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones de línea de crédito para metadata_id: {metadata_id}")

def insert_raw_falabella_linea_credito_to_staging(conn, metadata_id, source_id, raw_df):
    """Inserta los datos crudos de la cartola de Línea de Crédito Falabella en la tabla de staging."""
    cursor = conn.cursor()
    cols = ", ".join([f"`{col}`" for col in raw_df.columns])
    placeholders = ", ".join(["%s"] * len(raw_df.columns))
    query = f"""
    INSERT INTO staging_linea_credito_falabella (metadata_id, fuente_id, {cols})
    VALUES (%s, %s, {placeholders})
    """
    
    rows_to_insert = []
    for _, row in raw_df.iterrows():
        values = [metadata_id, source_id] + [None if pd.isna(val) else val for val in row.tolist()]
        rows_to_insert.append(tuple(values))

    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Se insertaron {len(rows_to_insert)} filas en staging_linea_credito_falabella para metadata_id: {metadata_id}")

def validate_staging_data(conn, metadata_id, expected_count, expected_sum_cargos, expected_sum_abonos):
    """Consulta la tabla de staging y valida el conteo y la suma de los montos."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM staging_linea_credito_falabella WHERE metadata_id = %s", (metadata_id,))
        actual_count = cursor.fetchone()[0]

        query_sum_cargos = "SELECT SUM(CAST(REPLACE(REPLACE(`Cargos`, '$', ''), '.', '') AS DECIMAL(15,2))) FROM staging_linea_credito_falabella WHERE metadata_id = %s"
        cursor.execute(query_sum_cargos, (metadata_id,))
        actual_sum_cargos_result = cursor.fetchone()[0]
        actual_sum_cargos = float(actual_sum_cargos_result) if actual_sum_cargos_result is not None else 0.0

        query_sum_abonos = "SELECT SUM(CAST(REPLACE(REPLACE(`Abonos`, '$', ''), '.', '') AS DECIMAL(15,2))) FROM staging_linea_credito_falabella WHERE metadata_id = %s"
        cursor.execute(query_sum_abonos, (metadata_id,))
        actual_sum_abonos_result = cursor.fetchone()[0]
        actual_sum_abonos = float(actual_sum_abonos_result) if actual_sum_abonos_result is not None else 0.0
        
        count_valid = actual_count == expected_count
        sum_cargos_valid = abs(actual_sum_cargos - expected_sum_cargos) < 0.01
        sum_abonos_valid = abs(actual_sum_abonos - expected_sum_abonos) < 0.01

        if count_valid:
            logging.info(f"VALIDACIÓN CONTEO: ÉXITO ({actual_count}/{expected_count})")
        else:
            logging.error(f"VALIDACIÓN CONTEO: FALLO ({actual_count}/{expected_count})")

        if sum_cargos_valid:
            logging.info(f"VALIDACIÓN SUMA CARGOS: ÉXITO ({actual_sum_cargos}/{expected_sum_cargos})")
        else:
            logging.error(f"VALIDACIÓN SUMA CARGOS: FALLO ({actual_sum_cargos}/{expected_sum_cargos})")

        if sum_abonos_valid:
            logging.info(f"VALIDACIÓN SUMA ABONOS: ÉXITO ({actual_sum_abonos}/{expected_sum_abonos})")
        else:
            logging.error(f"VALIDACIÓN SUMA ABONOS: FALLO ({actual_sum_abonos}/{expected_sum_abonos})")
        
        return count_valid and sum_cargos_valid and sum_abonos_valid
            
    except Exception as e:
        logging.error(f"Ocurrió un error durante la validación de staging: {e}", exc_info=True)
        return False
    finally:
        cursor.close()

def main():
    """
    Función principal para orquestar el procesamiento de archivos XLS.
    """
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\Banco falabella\linea de credito'
    source_name = 'Banco Falabella - Línea de Crédito'
    document_type = 'Bank Statement - Credit Line'

    xls_files = find_all_xls_files(xls_directory)
    if not xls_files:
        logging.info(f"No se encontraron archivos XLS/XLSX en: {xls_directory}")
        return

    logging.info(f"Se encontraron {len(xls_files)} archivos para procesar.")

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

                result = process_falabella_linea_credito_xls_file(xls_path)
                
                if result is None:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}. Omitiendo inserción y movimiento.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Parsing failed")
                    conn.rollback()
                    continue
                
                raw_df, processed_df, expected_count, expected_sum_cargos, expected_sum_abonos = result

                if processed_df is None or processed_df.empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}. Omitiendo inserción y movimiento.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - No data parsed")
                    conn.rollback()
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                insert_raw_falabella_linea_credito_to_staging(conn, metadata_id, source_id, raw_df)

                if not validate_staging_data(conn, metadata_id, expected_count, expected_sum_cargos, expected_sum_abonos):
                    logging.error(f"La validación de datos de staging falló para {os.path.basename(xls_path)}. Revirtiendo cambios.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Staging validation failed")
                    conn.rollback()
                    continue

                insert_linea_credito_transactions(conn, metadata_id, source_id, processed_df)
                
                conn.commit()

                processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
                os.makedirs(processed_dir, exist_ok=True)
                processed_filepath = os.path.join(processed_dir, os.path.basename(xls_path))
                shutil.move(xls_path, processed_filepath)
                logging.info(f"Archivo movido a procesados: {processed_filepath}")
                log_file_movement(xls_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Processed Successfully")

            except Exception as e:
                logging.error(f"Ocurrió un error mayor en el procesamiento de {os.path.basename(xls_path)}: {e}", exc_info=True)
                if conn.in_transaction:
                    conn.rollback()
                log_file_movement(xls_path, "N/A", "FAILED", f"Error al procesar: {e}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash or 'N/A'} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()