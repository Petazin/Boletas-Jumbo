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
    """Inserta los metadatos del archivo en la tabla común de metadatos."""
    cursor = conn.cursor()
    query = """
    INSERT INTO metadatos_cartolas_bancarias_raw (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type)
    cursor.execute(query, values)
    conn.commit()
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

        # --- INICIO DE LA CORRECCIÓN ---
        for index in range(len(df_initial_read)):
            # Convertir toda la fila a una cadena de texto en minúsculas
            row_str = ' '.join(map(str, df_initial_read.iloc[index].dropna())).lower()
            # Comprobar si todas las palabras clave (en minúsculas) están en la cadena de la fila
            if all(keyword.lower() in row_str for keyword in keywords_required):
                header_row_index = index
                break
        # --- FIN DE LA CORRECCIÓN ---
        
        if header_row_index == -1:
            logging.error(f"No se encontró la fila de cabecera de transacciones en {os.path.basename(xls_path)}.")
            return None

        logging.info(f"Fila de cabecera encontrada en el índice: {header_row_index}")

        df = pd.read_excel(xls_path, skiprows=header_row_index)
        
        df.columns = df.columns.str.strip()
        logging.info("Columnas detectadas: %s", df.columns.tolist())

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

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {len(df)} transacciones listas.")
        return df

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None

def insert_linea_credito_transactions(conn, metadata_id, source_id, df):
    """
    Inserta las transacciones de línea de crédito en la nueva tabla.
    """
    cursor = conn.cursor()
    query = """
    INSERT INTO transacciones_linea_credito_raw (
        metadata_id, fuente_id, fecha_transaccion, descripcion, cargos, abonos,
        monto_utilizado, tasa_diaria, intereses, linea_original_datos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for _, row in df.iterrows():
        original_line = ', '.join(map(str, row.values))
        values = (
            metadata_id, source_id, row.get('fecha_transaccion'), row.get('descripcion'),
            row.get('cargos'), row.get('abonos'), row.get('monto_utilizado'),
            row.get('tasa_diaria'), row.get('intereses'), original_line
        )
        cursor.execute(query, values)
    conn.commit()
    logging.info(f"Se insertaron {len(df)} transacciones de línea de crédito para metadata_id: {metadata_id}")

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
            try:
                file_hash = calculate_file_hash(xls_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado (hash existente), omitiendo: {os.path.basename(xls_path)}")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Skipped - Already Processed")
                    continue

                processed_df = process_falabella_linea_credito_xls_file(xls_path)
                
                if processed_df is None or processed_df.empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}. Omitiendo inserción y movimiento.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Parsing failed")
                    continue
                
                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                insert_linea_credito_transactions(conn, metadata_id, source_id, processed_df)
                
                processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
                os.makedirs(processed_dir, exist_ok=True)
                processed_filepath = os.path.join(processed_dir, os.path.basename(xls_path))
                shutil.move(xls_path, processed_filepath)
                logging.info(f"Archivo movido a procesados: {processed_filepath}")
                log_file_movement(xls_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Processed Successfully")

            except Exception as e:
                logging.error(f"Ocurrió un error mayor en el procesamiento de {os.path.basename(xls_path)}: {e}", exc_info=True)
                log_file_movement(xls_path, "N/A", "FAILED", f"Error al procesar: {e}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()
