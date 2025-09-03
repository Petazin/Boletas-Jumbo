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
    values = (source_id, file_path, file_hash, doc_type)
    cursor.execute(query, values)
    conn.commit()
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte valores monetarios, manejando el símbolo '."""
    if isinstance(value, str):
        value = value.replace('$', '').replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if value is not None else 0.0

def process_falabella_cc_xls_file(xls_path, source_id, metadata_id):
    """
    Procesa un archivo XLS de cartola de tarjeta de crédito de Banco Falabella.
    """
    logging.info(f"Iniciando procesamiento de XLS de Banco Falabella: {xls_path}")
    try:
        # Leer las primeras 50 filas para encontrar la cabecera dinámicamente.
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=50)
        
        # Palabras clave para identificar la fila de cabecera de transacciones.
        keywords_required = ["FECHA", "DESCRIPCION", "MONTO"]
        keywords_optional = ["CUOTAS PENDIENTES", "VALOR CUOTA"]
        header_row_index = -1

        # Buscar la fila de cabecera en todo el rango leído.
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

        logging.info(f"Fila de cabecera de transacciones encontrada en el índice: {header_row_index}")

        # Volver a leer el Excel, usando la fila de cabecera encontrada.
        df_transactions = pd.read_excel(xls_path, skiprows=header_row_index, header=0) 
        
        logging.info("Columnas del DataFrame de transacciones: %s", df_transactions.columns.tolist())

        # Mapeo de columnas del XLS a la base de datos.
        column_mapping = {
            'FECHA': 'fecha_cargo_original',
            'DESCRIPCION': 'descripcion_transaccion',
            'VALOR CUOTA': 'cargos_pesos',
            'CUOTAS PENDIENTES': 'cuotas_raw'
        }
        df_transactions.rename(columns=column_mapping, inplace=True)

        # Filtrar solo por las columnas que nos interesan y existen.
        columns_to_keep = [
            'fecha_cargo_original',
            'descripcion_transaccion',
            'cargos_pesos',
            'cuotas_raw'
        ]
        columns_to_keep = [col for col in columns_to_keep if col in df_transactions.columns]
        df_transactions = df_transactions[columns_to_keep]

        # Para esta versión, se asume cuota única. El valor original se guarda en 'cuotas_raw'.
        df_transactions['cuota_actual'] = 1
        df_transactions['total_cuotas'] = 1

        # Limpiar y convertir tipos de datos.
        df_transactions['fecha_cargo_original'] = pd.to_datetime(df_transactions['fecha_cargo_original'], format='%d-%m-%Y', errors='coerce')
        
        # La fecha de cargo de la cuota es la misma que la original para cuotas únicas.
        df_transactions['fecha_cargo_cuota'] = df_transactions['fecha_cargo_original']

        # Formatear las fechas a string YYYY-MM-DD para la BD.
        df_transactions['fecha_cargo_original'] = df_transactions['fecha_cargo_original'].dt.strftime('%Y-%m-%d')
        df_transactions['fecha_cargo_cuota'] = df_transactions['fecha_cargo_cuota'].dt.strftime('%Y-%m-%d')

        df_transactions['cargos_pesos'] = df_transactions['cargos_pesos'].apply(parse_and_clean_value)
        
        # Eliminar filas con fechas nulas que pueden ser resúmenes o basura.
        df_transactions.dropna(subset=['fecha_cargo_original'], inplace=True)

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {len(df_transactions)} transacciones listas para inserción.")
        return df_transactions

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}")
        return None

def insert_credit_card_transactions(conn, metadata_id, source_id, transactions_df):
    """
    Inserta las transacciones de tarjeta de crédito procesadas en la base de datos.
    """
    cursor = conn.cursor()
    query = """
    INSERT INTO transacciones_tarjeta_credito_raw (
        metadata_id, fuente_id, fecha_cargo_original, fecha_cargo_cuota, descripcion_transaccion, 
        categoria, cuota_actual, total_cuotas, cargos_pesos, monto_usd, tipo_cambio, pais
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for _, row in transactions_df.iterrows():
        values = (
            metadata_id,
            source_id,
            row.get('fecha_cargo_original'),
            row.get('fecha_cargo_cuota'),
            row.get('descripcion_transaccion'),
            row.get('categoria', None),
            row.get('cuota_actual'),
            row.get('total_cuotas'),
            row.get('cargos_pesos'),
            row.get('monto_usd', None),
            row.get('tipo_cambio', None),
            row.get('pais', None)
        )
        cursor.execute(query, values)
    conn.commit()
    logging.info(f"Se insertaron {len(transactions_df)} transacciones de tarjeta de crédito para metadata_id: {metadata_id}")

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
            try:
                file_hash = calculate_file_hash(xls_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado (hash existente), omitiendo: {os.path.basename(xls_path)}")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Skipped - Already Processed")
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                
                processed_df = process_falabella_cc_xls_file(xls_path, source_id, metadata_id)
                
                if processed_df is None or processed_df.empty:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - Parsing failed")
                    continue
                
                insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                
                processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
                os.makedirs(processed_dir, exist_ok=True)
                processed_filepath = os.path.join(processed_dir, os.path.basename(xls_path))
                shutil.move(xls_path, processed_filepath)
                logging.info(f"Archivo movido a la carpeta de procesados: {processed_filepath}")
                log_file_movement(xls_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")

                logging.info(f"Proceso de ingesta completado con éxito para: {os.path.basename(xls_path)}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Processed Successfully")

            except Exception as e:
                logging.error(f"Ocurrió un error procesando el archivo {os.path.basename(xls_path)}: {e}")
                log_file_movement(xls_path, "N/A", "FAILED", f"Error al procesar: {e}")
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()