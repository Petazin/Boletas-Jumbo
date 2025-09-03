import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement
from database_utils import db_connection
from collections import defaultdict
from datetime import datetime


# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración del logger para el estado de la ingesta
ingestion_status_logger = logging.getLogger('ingestion_status')
ingestion_status_logger.setLevel(logging.INFO)
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
    query = "SELECT 1 FROM metadatos_cartolas_bancarias_raw WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone() is not None
    cursor.close()
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
        conn.commit()
        return cursor.lastrowid

def insert_metadata(conn, source_id, file_path, file_hash, doc_type):
    """Inserta los metadatos del archivo, incluyendo su hash y tipo de documento."""
    cursor = conn.cursor()
    query = """
    INSERT INTO metadatos_cartolas_bancarias_raw (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    # Corregido para usar os.path.basename y ser consistente
    values = (source_id, os.path.basename(file_path), file_hash, doc_type)
    cursor.execute(query, values)
    conn.commit()
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

def process_falabella_cuenta_corriente_xls_file(xls_path, source_id, metadata_id):
    """
    Procesa un archivo XLS de cartola de Cuenta Corriente de Banco Falabella.
    """
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
            return None

        logging.info(f"Fila de cabecera de transacciones encontrada en el índice: {header_row_index}")

        df_transactions = pd.read_excel(xls_path, skiprows=header_row_index, header=0) 
        
        df_transactions = df_transactions.loc[:, ~df_transactions.columns.str.contains('^Unnamed')]
        if 'nan' in df_transactions.columns:
            df_transactions = df_transactions.drop(columns=['nan'])

        logging.info("Columnas del DataFrame de transacciones (después de limpiar Unnamed/nan): %s", df_transactions.columns.tolist())

        column_mapping = {
            'Fecha': 'fecha_transaccion_str',
            'Descripcion': 'descripcion_transaccion',
            'Cargo': 'cargos_pesos',
            'Abono': 'abonos_pesos',
            'Saldo': 'saldo_pesos'
        }
        df_transactions.rename(columns=column_mapping, inplace=True)

        columns_to_keep = [
            'fecha_transaccion_str', 'descripcion_transaccion', 'cargos_pesos',
            'abonos_pesos', 'saldo_pesos'
        ]
        columns_to_keep = [col for col in columns_to_keep if col in df_transactions.columns]
        df_transactions = df_transactions[columns_to_keep]

        df_transactions['fecha_transaccion_str'] = pd.to_datetime(df_transactions['fecha_transaccion_str'], format='%d-%m-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
        df_transactions.dropna(subset=['fecha_transaccion_str'], inplace=True)

        df_transactions['cargos_pesos'] = df_transactions['cargos_pesos'].apply(parse_and_clean_value)
        df_transactions['abonos_pesos'] = df_transactions['abonos_pesos'].apply(parse_and_clean_value)
        df_transactions['saldo_pesos'] = df_transactions['saldo_pesos'].apply(parse_and_clean_value)
        
        # --- INICIO DE LA CORRECCIÓN ---
        # Reemplazar todos los NaN restantes con None para compatibilidad con SQL.
        df_transactions = df_transactions.astype(object).where(pd.notnull(df_transactions), None)
        # --- FIN DE LA CORRECCIÓN ---

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {len(df_transactions)} transacciones listas para inserción.")
        return df_transactions

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None

def insert_bank_account_transactions(conn, metadata_id, source_id, transactions_df):
    """
    Inserta las transacciones de cuenta bancaria procesadas en la base de datos.
    """
    cursor = conn.cursor()
    query = """
    INSERT INTO transacciones_cuenta_bancaria_raw (
        metadata_id, fuente_id, fecha_transaccion_str, descripcion_transaccion, 
        canal_o_sucursal, cargos_pesos, abonos_pesos, saldo_pesos, linea_original_datos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for _, row in transactions_df.iterrows():
        values = (
            metadata_id,
            source_id,
            row.get('fecha_transaccion_str'),
            row.get('descripcion_transaccion'),
            row.get('canal_o_sucursal', None),
            row.get('cargos_pesos'),
            row.get('abonos_pesos'),
            row.get('saldo_pesos'),
            str(row.to_dict()) # Guardar la fila original como string
        )
        cursor.execute(query, values)
    conn.commit()
    logging.info(f"Se insertaron {len(transactions_df)} transacciones de cuenta bancaria para metadata_id: {metadata_id}")

def main():
    """
    Función principal para orquestar el procesamiento de archivos XLS de Cuenta Corriente de Banco Falabella.
    """
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\Banco falabella\Cuenta Corriente'
    source_name = 'Banco Falabella - Cuenta Corriente'
    document_type = 'Bank Statement - Checking Account'

    xls_files = find_all_xls_files(xls_directory)

    if not xls_files:
        logging.info(f"No se encontraron archivos XLS/XLSX en: {xls_directory}")
        return

    logging.info(f"Se encontraron {len(xls_files)} archivos XLS/XLSX para procesar.")

    with db_connection() as conn:
        source_id = get_source_id(conn, source_name)
        for xls_path in xls_files:
            try:
                file_hash = calculate_file_hash(xls_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado (hash existente), omitiendo: {os.path.basename(xls_path)}")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Skipped - Already Processed")
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                
                processed_df = process_falabella_cuenta_corriente_xls_file(xls_path, source_id, metadata_id)
                
                if processed_df is None or processed_df.empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Parsing failed")
                    continue
                
                insert_bank_account_transactions(conn, metadata_id, source_id, processed_df)
                
                processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
                os.makedirs(processed_dir, exist_ok=True)
                processed_filepath = os.path.join(processed_dir, os.path.basename(xls_path))
                shutil.move(xls_path, processed_filepath)
                logging.info(f"Archivo movido a la carpeta de procesados: {processed_filepath}")
                log_file_movement(xls_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Processed Successfully")

            except Exception as e:
                logging.error(f"Ocurrió un error procesando el archivo {os.path.basename(xls_path)}: {e}", exc_info=True)
                log_file_movement(xls_path, "N/A", "FAILED", f"Error al procesar: {e}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()
