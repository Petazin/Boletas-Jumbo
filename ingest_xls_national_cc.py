import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement
from database_utils import db_connection
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def find_all_xls_files(directory):
    xls_files = []
    if not os.path.isdir(directory):
        logging.warning(f"El directorio no existe: {directory}")
        return xls_files
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.xls', '.xlsx')):
            xls_files.append(os.path.join(directory, filename))
    return xls_files

def is_file_processed(conn, file_hash):
    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT 1 FROM metadatos_cartolas_bancarias_raw WHERE file_hash = %s", (file_hash,))
    result = cursor.fetchone() is not None
    cursor.close()
    return result

def get_source_id(conn, source_name):
    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT fuente_id FROM fuentes WHERE nombre_fuente = %s", (source_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO fuentes (nombre_fuente, tipo_fuente) VALUES (%s, 'Tarjeta de Credito')", (source_name,))
        conn.commit()
        return cursor.lastrowid

def insert_metadata(conn, source_id, file_path, file_hash, doc_type):
    cursor = conn.cursor()
    query = """
    INSERT INTO metadatos_cartolas_bancarias_raw (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type)
    cursor.execute(query, values)
    return cursor.lastrowid

def parse_and_clean_value(value):
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if pd.notna(value) else 0.0

def load_abono_mappings(conn):
    abono_descriptions = set()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT description FROM abonos_mapping")
            rows = cursor.fetchall()
            for row in rows:
                abono_descriptions.add(row['description'].strip())
        logging.info(f"Cargadas {len(abono_descriptions)} descripciones de abono: {abono_descriptions}")
    except Exception as e:
        logging.error(f"Error al cargar mapeos de abonos: {e}")
    return abono_descriptions

def process_national_cc_xls_file(xls_path, abono_descriptions):
    logging.info(f"Iniciando procesamiento de XLS nacional: {xls_path}")
    try:
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=50)
        keywords_required = ["Fecha", "Descripción"]
        header_row_index = -1
        for index in range(10, len(df_initial_read)):
            row_str = ' '.join(df_initial_read.iloc[index].astype(str).dropna())
            if all(keyword in row_str for keyword in keywords_required):
                header_row_index = index
                break
        if header_row_index == -1:
            logging.error(f"No se encontró cabecera en {os.path.basename(xls_path)}.")
            return None

        df = pd.read_excel(xls_path, skiprows=header_row_index, header=0)
        df.columns = [str(col).strip() for col in df.columns]
        
        column_mapping = {
            'Fecha': 'fecha_cargo_original',
            'Descripción': 'descripcion_transaccion',
            'Cuotas': 'cuotas_str',
            'Monto ($)': 'monto_bruto'
        }
        df.rename(columns=column_mapping, inplace=True)

        if not all(col in df.columns for col in ['fecha_cargo_original', 'descripcion_transaccion', 'monto_bruto']):
            logging.error(f"Columnas esenciales no encontradas en {os.path.basename(xls_path)}.")
            return None

        df['fecha_cargo_original'] = pd.to_datetime(df['fecha_cargo_original'], errors='coerce', dayfirst=True)
        df.dropna(subset=['fecha_cargo_original', 'descripcion_transaccion'], inplace=True)

        df['cuota_actual'] = df['cuotas_str'].astype(str).apply(lambda x: int(x.split('/')[0]) if pd.notna(x) and '/' in x else 1)
        df['total_cuotas'] = df['cuotas_str'].astype(str).apply(lambda x: int(x.split('/')[1]) if pd.notna(x) and '/' in x else 1)

        df['fecha_cargo_cuota'] = df.apply(
            lambda row: row['fecha_cargo_original'] + relativedelta(months=row['cuota_actual'] - 1) if pd.notna(row['fecha_cargo_original']) else pd.NaT,
            axis=1
        )

        # --- LÓGICA DE SEPARACIÓN DE CARGOS/ABONOS ---
        # El archivo XLS no distingue entre cargos y abonos en columnas separadas.
        # Se utiliza la tabla `abonos_mapping` para identificar qué transacciones son abonos.
        # Si la descripción de la transacción existe en el set `abono_descriptions`,
        # el monto se asigna a `abonos_pesos`; de lo contrario, a `cargos_pesos`.
        df['cargos_pesos'] = df.apply(lambda row: parse_and_clean_value(row['monto_bruto']) if str(row['descripcion_transaccion']).strip() not in abono_descriptions else 0, axis=1)
        df['abonos_pesos'] = df.apply(lambda row: parse_and_clean_value(row['monto_bruto']) if str(row['descripcion_transaccion']).strip() in abono_descriptions else 0, axis=1)

        df_final = df.astype(object).where(pd.notnull(df), None)
        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. {len(df_final)} transacciones listas.")
        return df_final

    except Exception as e:
        logging.error(f"Error procesando {os.path.basename(xls_path)}: {e}", exc_info=True)
        return None

def insert_credit_card_transactions(conn, metadata_id, source_id, df):
    cursor = conn.cursor()
    query = """
    INSERT INTO transacciones_tarjeta_credito_raw (
        metadata_id, fuente_id, fecha_cargo_original, fecha_cargo_cuota, 
        descripcion_transaccion, cuota_actual, total_cuotas, cargos_pesos, abonos_pesos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows_to_insert = []
    for _, row in df.iterrows():
        rows_to_insert.append((
            metadata_id, source_id,
            row.get('fecha_cargo_original'), row.get('fecha_cargo_cuota'),
            row.get('descripcion_transaccion'), row.get('cuota_actual'),
            row.get('total_cuotas'), row.get('cargos_pesos'), row.get('abonos_pesos')
        ))
    
    if rows_to_insert:
        cursor.executemany(query, rows_to_insert)
        logging.info(f"Insertadas {len(rows_to_insert)} transacciones para metadata_id: {metadata_id}")

def main():
    xls_directory = r'c:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\tarjeta de credito\nacional'
    source_name = 'Banco de Chile - Tarjeta Credito Nacional'
    document_type = 'National Credit Card Statement'

    with db_connection() as conn:
        abono_descriptions = load_abono_mappings(conn)
        source_id = get_source_id(conn, source_name)
        xls_files = find_all_xls_files(xls_directory)

        if not xls_files:
            logging.info(f"No se encontraron archivos XLS en: {xls_directory}")
            return

        logging.info(f"Se encontraron {len(xls_files)} archivos XLS para procesar.")

        for xls_path in xls_files:
            file_hash = None
            try:
                conn.start_transaction()
                file_hash = calculate_file_hash(xls_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado, omitiendo: {os.path.basename(xls_path)}")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | STATUS: Skipped")
                    conn.rollback()
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                processed_df = process_national_cc_xls_file(xls_path, abono_descriptions)

                if processed_df is not None and not processed_df.empty:
                    insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                    conn.commit()
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Processed Successfully")
                    
                    processed_dir = os.path.join(os.path.dirname(xls_path), 'procesados')
                    os.makedirs(processed_dir, exist_ok=True)
                    shutil.move(xls_path, os.path.join(processed_dir, os.path.basename(xls_path)))
                    logging.info(f"Archivo movido a procesados: {os.path.basename(xls_path)}")
                else:
                    logging.warning(f"No se procesaron transacciones para {os.path.basename(xls_path)}.")
                    ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash} | STATUS: Failed - No data parsed")
                    conn.rollback()

            except Exception as e:
                logging.error(f"Error CRÍTICO procesando {os.path.basename(xls_path)}: {e}", exc_info=True)
                if conn.in_transaction:
                    conn.rollback()
                ingestion_status_logger.info(f"FILE: {os.path.basename(xls_path)} | HASH: {file_hash or 'N/A'} | STATUS: Failed - {e}")

if __name__ == '__main__':
    main()
