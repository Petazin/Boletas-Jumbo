import pandas as pd
import os
import logging
import hashlib
import shutil
from database_utils import db_connection
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from config import PROCESSED_BANK_STATEMENTS_DIR

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    """Limpia y convierte valores monetarios."""
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if value is not None else 0.0

def process_international_cc_xls_file(xls_path, source_id, metadata_id):
    """
    Procesa un archivo XLS de cartola de tarjeta de crédito internacional.
    """
    logging.info(f"Iniciando procesamiento de XLS internacional: {xls_path}")
    try:
        # Leer las primeras 50 filas del archivo Excel sin cabecera para buscar la tabla de transacciones.
        df_initial_read = pd.read_excel(xls_path, header=None, nrows=50)
        
        # Buscar la fila que contiene las cabeceras de las transacciones.
        keywords_required = ["Fecha", "Descripción"]
        keywords_optional = ["Monto", "Cargo", "Abono", "Importe"]
        header_row_index = -1

        # Iterar desde la fila 18 (índice 17) en adelante.
        for index in range(17, len(df_initial_read)):
            row = df_initial_read.iloc[index]
            row_str = row.astype(str).str.cat(sep=' ')
            
            if all(keyword in row_str for keyword in keywords_required) and \
               any(keyword in row_str for keyword in keywords_optional):
                header_row_index = index
                break
        
        if header_row_index == -1:
            logging.error(f"No se encontró la fila de cabecera de transacciones en {os.path.basename(xls_path)} con las palabras clave especificadas.")
            return None

        logging.info(f"Fila de cabecera de transacciones encontrada en el índice: {header_row_index}")

        # Volver a leer el Excel, esta vez especificando la fila de cabecera.
        df_transactions = pd.read_excel(xls_path, skiprows=header_row_index, header=0) 
        
        logging.info("DataFrame de transacciones (primeras 10 filas):")
        logging.info(df_transactions.head(10))
        logging.info("Columnas del DataFrame de transacciones:")
        logging.info(df_transactions.columns.tolist())

        # Renombrar columnas para que coincidan con el esquema de la BD
        column_mapping = {
            'Fecha': 'fecha_cargo_original', # Fecha del XLS es la fecha original de la compra
            'Descripción': 'descripcion_transaccion',
            'Categoría': 'categoria',
            'Cuotas': 'cuotas_raw', # Nombre temporal para la columna original de Cuotas
            'Monto Moneda Origen': 'cargos_pesos', # Monto en CLP
            'Monto (USD)': 'monto_usd', # Monto en USD
            'País': 'pais'
        }
        df_transactions.rename(columns=column_mapping, inplace=True)

        # Filtrar el DataFrame para quedarse solo con las columnas que realmente necesitamos y existen.
        columns_to_keep = [
            'fecha_cargo_original',
            'descripcion_transaccion',
            'categoria',
            'cargos_pesos',
            'monto_usd',
            'pais'
        ]
        # Asegurarse de que las columnas existan antes de seleccionarlas
        columns_to_keep = [col for col in column_mapping.values() if col in df_transactions.columns]
        df_transactions = df_transactions[columns_to_keep]

        # Manejar la ausencia de 'Cuotas' (cuotas_raw) en cartolas internacionales.
        if 'cuotas_raw' in df_transactions.columns:
            df_transactions['cuota_actual'] = df_transactions['cuotas_raw'].astype(str).apply(lambda x: int(x.split('/')[0]) if '/' in x else 1)
            df_transactions['total_cuotas'] = df_transactions['cuotas_raw'].astype(str).apply(lambda x: int(x.split('/')[1]) if '/' in x else 1)
        else:
            # Si la columna 'Cuotas' no existe, se asume que es una cuota 1/1.
            df_transactions['cuota_actual'] = 1
            df_transactions['total_cuotas'] = 1

        # Limpiar y convertir tipos de datos
        # Convertir fecha_cargo_original a datetime primero para poder hacer cálculos de fecha
        df_transactions['fecha_cargo_original'] = pd.to_datetime(df_transactions['fecha_cargo_original'], errors='coerce')
        
        # Calcular fecha_cargo_cuota
        # fecha_cargo_cuota = fecha_cargo_original + (cuota_actual - 1) meses
        df_transactions['fecha_cargo_cuota'] = df_transactions.apply(
            lambda row: row['fecha_cargo_original'] + relativedelta(months=row['cuota_actual'] - 1)
            if pd.notna(row['fecha_cargo_original']) and row['cuota_actual'] > 0 else pd.NaT,
            axis=1
        )

        # Formatear las fechas a string YYYY-MM-DD para la BD
        df_transactions['fecha_cargo_original'] = df_transactions['fecha_cargo_original'].dt.strftime('%Y-%m-%d')
        df_transactions['fecha_cargo_cuota'] = df_transactions['fecha_cargo_cuota'].dt.strftime('%Y-%m-%d')

        df_transactions['cargos_pesos'] = df_transactions['cargos_pesos'].apply(parse_and_clean_value)
        
        # Manejar la ausencia de monto_usd y pais en cartolas nacionales
        if 'monto_usd' in df_transactions.columns:
            df_transactions['monto_usd'] = df_transactions['monto_usd'].apply(parse_and_clean_value)
            # Calcular tipo_cambio (evitar división por cero)
            df_transactions['tipo_cambio'] = df_transactions.apply(
                lambda row: row['cargos_pesos'] / row['monto_usd'] if row['monto_usd'] != 0 else 0.0,
                axis=1
            )
        else:
            df_transactions['monto_usd'] = None
            df_transactions['tipo_cambio'] = None
        
        if 'pais' not in df_transactions.columns:
            df_transactions['pais'] = None

        # Eliminar filas con fechas nulas después de la conversión (posibles filas de resumen o basura)
        df_transactions.dropna(subset=['fecha_cargo_original'], inplace=True)

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. DataFrame listo para inserción.")
        return df_transactions

    except Exception as e:
        logging.error(f"Error al procesar el archivo XLS {os.path.basename(xls_path)}: {e}")
        return None

def insert_credit_card_transactions(conn, metadata_id, source_id, transactions_df):
    """
    Inserta las transacciones de tarjeta de crédito procesadas en la base de datos.
    """
    # Reemplazar todos los NaN con None para compatibilidad con la base de datos
    transactions_df = transactions_df.where(pd.notnull(transactions_df), None)
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
            row.get('categoria'),
            row.get('cuota_actual'),
            row.get('total_cuotas'),
            row.get('cargos_pesos'),
            row.get('monto_usd'),
            row.get('tipo_cambio'),
            row.get('pais')
        )
        cursor.execute(query, values)
    conn.commit()
    logging.info(f"Se insertaron {len(transactions_df)} transacciones de tarjeta de crdito para metadata_id: {metadata_id}")

def main():
    """
    Función principal para orquestar el procesamiento de archivos XLS.
    """
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\tarjeta de credito\internacional'
    source_name = 'Banco de Chile - Tarjeta Credito Internacional'
    document_type = 'International Credit Card Statement'

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
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                
                processed_df = process_international_cc_xls_file(xls_path, source_id, metadata_id) # Renamed function call
                
                if processed_df is None:
                    logging.error(f"Fallo el procesamiento de {os.path.basename(xls_path)}.")
                    continue
                
                insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                
                # Mover el archivo XLS procesado a la carpeta de archivos procesados
                processed_filepath = os.path.join(PROCESSED_BANK_STATEMENTS_DIR, os.path.basename(xls_path))
                os.makedirs(os.path.dirname(processed_filepath), exist_ok=True)
                shutil.move(xls_path, processed_filepath)
                logging.info(f"Archivo movido a la carpeta de procesados: {processed_filepath}")

                logging.info(f"Proceso de ingesta completado con éxito para: {os.path.basename(xls_path)}")

            except Exception as e:
                logging.error(f"Ocurrió un error procesando el archivo {os.path.basename(xls_path)}: {e}")

if __name__ == '__main__':
    main()
