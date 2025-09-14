import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement, generate_standardized_filename
from database_utils import db_connection
from collections import defaultdict
from datetime import datetime

# --- CONFIGURACIÓN ---
DOCUMENT_TYPE = 'CTA_CORRIENTE_FALABELLA'

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
    query = "SELECT 1 FROM raw_metadatos_documentos WHERE file_hash = %s"
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
    INSERT INTO raw_metadatos_documentos (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type_desc)
    cursor.execute(query, values)
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte valores monetarios, manejando el símbolo '.'"""
    if isinstance(value, str):
        value = value.replace('$', '').replace(' ', '').replace('.', '').replace(',', '.')
        
        if value.endswith('-'):
            value = '-' + value[:-1]
        
        try:
            return float(value)
        except ValueError:
            return 0.0
    return value if pd.notna(value) else 0.0

def process_falabella_cuenta_corriente_xls_file(xls_path):
    """Procesa un XLS de Cta Corriente y retorna DFs, métricas y el período."""
    logging.info(f"Iniciando procesamiento de XLS de Cuenta Corriente de Banco Falabella: {xls_path}")
    try:
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=50)
        
        keywords_required = ["Fecha", "Descripcion", "Cargo", "Abono", "Saldo"]
        header_row_index = -1

        for index in range(len(df_initial_read)):
            row = df_initial_read.iloc[index]
            row_str = row.astype(str).str.cat(sep=' ')
            
            if all(keyword in row_str for keyword in keywords_required):
                header_row_index = index
                break
        
        if header_row_index == -1:
            logging.error(f"No se encontró la fila de cabecera de transacciones en {os.path.basename(xls_path)}.")
            return None, None, 0, 0, 0, None

        df_transactions = pd.read_excel(xls_path, skiprows=header_row_index, header=0)
        raw_df = df_transactions.copy()
        
        df_transactions = df_transactions.loc[:, ~df_transactions.columns.str.contains('^Unnamed')]
        if 'nan' in df_transactions.columns:
            df_transactions = df_transactions.drop(columns=['nan'])

        column_mapping = {
            'Fecha': 'fecha_transaccion_str',
            'Descripcion': 'descripcion_transaccion',
            'Cargo': 'cargos_pesos',
            'Abono': 'abonos_pesos',
            'Saldo': 'saldo_pesos'
        }
        df_transactions.rename(columns=column_mapping, inplace=True)

        df_transactions['fecha_transaccion'] = pd.to_datetime(df_transactions['fecha_transaccion_str'], format='%d-%m-%Y', errors='coerce')
        df_transactions.dropna(subset=['fecha_transaccion'], inplace=True)

        document_period = df_transactions['fecha_transaccion'].max()

        df_transactions['fecha_transaccion_str'] = df_transactions['fecha_transaccion'].dt.strftime('%Y-%m-%d')

        df_transactions['cargos_pesos'] = df_transactions['cargos_pesos'].apply(parse_and_clean_value)
        df_transactions['abonos_pesos'] = df_transactions['abonos_pesos'].apply(parse_and_clean_value)
        df_transactions['saldo_pesos'] = df_transactions['saldo_pesos'].apply(parse_and_clean_value)
        
        df_transactions = df_transactions.astype(object).where(pd.notnull(df_transactions), None)

        expected_count = len(df_transactions)
        expected_sum_cargos = df_transactions['cargos_pesos'].sum()
        expected_sum_abonos = df_transactions['abonos_pesos'].sum()

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {expected_count} transacciones. Período: {document_period.strftime('%Y-%m') if document_period else 'N/A'}")
        return raw_df, df_transactions, expected_count, expected_sum_cargos, expected_sum_abonos, document_period

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None, None, 0, 0, 0, None

def insert_bank_account_transactions(conn, metadata_id, source_id, transactions_df):
    """Inserta las transacciones de cuenta bancaria procesadas en la base de datos."""
    cursor = conn.cursor()
    query = """
    INSERT INTO raw_transacciones_cta_corriente (
        metadata_id, fuente_id, fecha_transaccion_str, descripcion_transaccion, 
        canal_o_sucursal, cargos_pesos, abonos_pesos, saldo_pesos, linea_original_datos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in transactions_df.iterrows():
        rows_to_insert.append((
            metadata_id, source_id,
            row.get('fecha_transaccion_str'), row.get('descripcion_transaccion'),
            row.get('canal_o_sucursal', None), row.get('cargos_pesos'),
            row.get('abonos_pesos'), row.get('saldo_pesos'),
            str(row.to_dict())
        ))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones de cuenta bancaria para metadata_id: {metadata_id}")

def insert_raw_falabella_cuenta_corriente_to_staging(conn, metadata_id, source_id, raw_df):
    """Inserta los datos crudos de la cartola de Cuenta Corriente Falabella en la tabla de staging."""
    cursor = conn.cursor()
    cols = ", ".join([f'`{col}`' for col in raw_df.columns])
    placeholders = ", ".join(["%s"] * len(raw_df.columns))
    query = f"""
    INSERT INTO staging_cta_corriente_falabella (metadata_id, fuente_id, {cols})
    VALUES (%s, %s, {placeholders})
    """
    
    rows_to_insert = []
    for _, row in raw_df.iterrows():
        values = [metadata_id, source_id] + [None if pd.isna(val) else val for val in row.tolist()]
        rows_to_insert.append(tuple(values))

    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Se insertaron {len(rows_to_insert)} filas en staging_cta_corriente_falabella para metadata_id: {metadata_id}")

def validate_staging_data(conn, metadata_id, expected_count, expected_sum_cargos, expected_sum_abonos):
    """Consulta la tabla de staging y valida el conteo y la suma de los montos."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM staging_cta_corriente_falabella WHERE metadata_id = %s", (metadata_id,))
        actual_count = cursor.fetchone()[0]

        query_sum_cargos = "SELECT SUM(CAST(REPLACE(REPLACE(`Cargo`, '$', ''), '.', '') AS DECIMAL(15,2))) FROM staging_cta_corriente_falabella WHERE metadata_id = %s"
        cursor.execute(query_sum_cargos, (metadata_id,))
        actual_sum_cargos_result = cursor.fetchone()[0]
        actual_sum_cargos = float(actual_sum_cargos_result) if actual_sum_cargos_result is not None else 0.0

        query_sum_abonos = "SELECT SUM(CAST(REPLACE(REPLACE(`Abono`, '$', ''), '.', '') AS DECIMAL(15,2))) FROM staging_cta_corriente_falabella WHERE metadata_id = %s"
        cursor.execute(query_sum_abonos, (metadata_id,))
        actual_sum_abonos_result = cursor.fetchone()[0]
        actual_sum_abonos = float(actual_sum_abonos_result) if actual_sum_abonos_result is not None else 0.0
        
        count_valid = actual_count == expected_count
        sum_cargos_valid = abs(actual_sum_cargos - expected_sum_cargos) < 0.01
        sum_abonos_valid = abs(actual_sum_abonos - expected_sum_abonos) < 0.01

        # ... (logging remains the same)
        
        return count_valid and sum_cargos_valid and sum_abonos_valid
            
    except Exception as e:
        logging.error(f"Ocurrió un error durante la validación de staging: {e}", exc_info=True)
        return False
    finally:
        cursor.close()

def main():
    """Función principal para orquestar el procesamiento de archivos XLS de Cuenta Corriente de Banco Falabella."""
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\Banco falabella\Cuenta Corriente'
    source_name = 'Banco Falabella - Cuenta Corriente'
    doc_type_desc = 'Bank Statement - Checking Account'

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

                result = process_falabella_cuenta_corriente_xls_file(xls_path)
                
                if result is None or result[1] is None or result[1].empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Parsing failed or no data")
                    conn.rollback()
                    continue
                
                raw_df, processed_df, expected_count, expected_sum_cargos, expected_sum_abonos, document_period = result

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, doc_type_desc)
                insert_raw_falabella_cuenta_corriente_to_staging(conn, metadata_id, source_id, raw_df)
                
                if not validate_staging_data(conn, metadata_id, expected_count, expected_sum_cargos, expected_sum_abonos):
                    logging.error(f"La validación de datos de staging falló para {os.path.basename(xls_path)}. Revirtiendo.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Staging validation failed")
                    conn.rollback()
                    continue

                insert_bank_account_transactions(conn, metadata_id, source_id, processed_df)
                
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
                ingestion_status_logger.info(f"FILE: {new_filename} | HASH: {file_hash} | STATUS: Processed Successfully")

            except Exception as e:
                logging.error(f"Ocurrió un error CRÍTICO procesando el archivo {os.path.basename(xls_path)}: {e}", exc_info=True)
                if conn.in_transaction:
                    conn.rollback()
                log_file_movement(xls_path, "N/A", "FAILED", f"Error al procesar: {e}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash or 'N/A'} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()
