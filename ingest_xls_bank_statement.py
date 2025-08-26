import pandas as pd
import os
import logging
import hashlib
from database_utils import db_connection
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta

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
    query = "SELECT 1 FROM bank_statement_metadata_raw WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone() is not None
    cursor.close()
    return result

def get_source_id(conn, source_name):
    """Obtiene el ID de la fuente, creándolo si no existe."""
    cursor = conn.cursor(buffered=True)
    query = "SELECT source_id FROM sources WHERE source_name = %s"
    cursor.execute(query, (source_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        insert_query = "INSERT INTO sources (source_name) VALUES (%s)"
        cursor.execute(insert_query, (source_name,))
        conn.commit()
        return cursor.lastrowid

def insert_metadata(conn, source_id, file_path, file_hash, doc_type):
    """Inserta los metadatos del archivo, incluyendo su hash y tipo de documento."""
    cursor = conn.cursor()
    query = """
    INSERT INTO bank_statement_metadata_raw (source_id, file_path, status, file_hash, document_type)
    VALUES (%s, %s, %s, %s, %s)
    """
    values = (source_id, file_path, 'processed', file_hash, doc_type)
    cursor.execute(query, values)
    conn.commit()
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte valores monetarios."""
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if value is not None else 0.0

def process_xls_file(xls_path, source_id, metadata_id):
    """
    Procesa un archivo XLS de cartola de tarjeta de crédito.
    Esta función buscará la fila de cabecera de las transacciones y leerá el Excel a partir de ahí.
    """
    logging.info(f"Iniciando procesamiento de XLS: {xls_path}")
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

        # Volver a leer el Excel, esta vez especificando la fila de cabecera y las columnas relevantes.
        # usecols = [1, 2, 3, 6, 7] para seleccionar las columnas B, C, D, G, H (índices 1, 2, 3, 6, 7).
        # Columnas: Categoría (B), Fecha (C), Descripción (D), Cuotas (G), Monto ($) (H)
        df_transactions = pd.read_excel(xls_path, skiprows=header_row_index, header=0, usecols=[1, 2, 3, 6, 7])
        
        logging.info("DataFrame de transacciones (primeras 10 filas):")
        logging.info(df_transactions.head(10))
        logging.info("Columnas del DataFrame de transacciones:")
        logging.info(df_transactions.columns.tolist())

        # Renombrar columnas para que coincidan con el esquema de la BD
        column_mapping = {
            'Fecha': 'original_charge_date', # Fecha del XLS es la fecha original de la compra
            'Descripción': 'transaction_description',
            'Categoría': 'category',
            'Cuotas': 'installments_raw', # Nombre temporal para la columna original de Cuotas
            'Monto ($)': 'charges_pesos' # Asumimos que Monto ($) son cargos
        }
        df_transactions.rename(columns=column_mapping, inplace=True)

        # Parsear la columna 'Cuotas' en current_installment y total_installments
        df_transactions['current_installment'] = df_transactions['installments_raw'].astype(str).apply(lambda x: int(x.split('/')[0]) if '/' in x else 1)
        df_transactions['total_installments'] = df_transactions['installments_raw'].astype(str).apply(lambda x: int(x.split('/')[1]) if '/' in x else 1)

        # Limpiar y convertir tipos de datos
        # Convertir original_charge_date a datetime primero para poder hacer cálculos de fecha
        df_transactions['original_charge_date'] = pd.to_datetime(df_transactions['original_charge_date'], errors='coerce')
        
        # Calcular installment_charge_date
        # installment_charge_date = original_charge_date + (current_installment - 1) meses
        df_transactions['installment_charge_date'] = df_transactions.apply(
            lambda row: row['original_charge_date'] + relativedelta(months=row['current_installment'] - 1)
            if pd.notna(row['original_charge_date']) and row['current_installment'] > 0 else pd.NaT,
            axis=1
        )

        # Formatear las fechas a string YYYY-MM-DD para la BD
        df_transactions['original_charge_date'] = df_transactions['original_charge_date'].dt.strftime('%Y-%m-%d')
        df_transactions['installment_charge_date'] = df_transactions['installment_charge_date'].dt.strftime('%Y-%m-%d')

        df_transactions['charges_pesos'] = df_transactions['charges_pesos'].apply(parse_and_clean_value)
        
        # Eliminar filas con fechas nulas después de la conversión (posibles filas de resumen o basura)
        df_transactions.dropna(subset=['original_charge_date'], inplace=True)

        logging.info(f"Parseo de {os.path.basename(xls_path)} completado. DataFrame listo para inserción.")
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
    INSERT INTO credit_card_transactions_raw (
        metadata_id, source_id, original_charge_date, installment_charge_date, transaction_description, 
        category, current_installment, total_installments, charges_pesos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for _, row in transactions_df.iterrows():
        values = (
            metadata_id,
            source_id,
            row.get('original_charge_date'),
            row.get('installment_charge_date'),
            row.get('transaction_description'),
            row.get('category'),
            row.get('current_installment'),
            row.get('total_installments'),
            row.get('charges_pesos')
        )
        cursor.execute(query, values)
    conn.commit()
    logging.info(f"Se insertaron {len(transactions_df)} transacciones de tarjeta de crdito para metadata_id: {metadata_id}")

def main():
    """
    Función principal para orquestar el procesamiento de archivos XLS.
    """
    xls_directory = r'C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\tarjeta de credito\nacional'
    source_name = 'Banco de Chile - Tarjeta Credito Nacional'
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
                    continue

                metadata_id = insert_metadata(conn, source_id, xls_path, file_hash, document_type)
                
                processed_df = process_xls_file(xls_path, source_id, metadata_id)
                
                if processed_df is None:
                    logging.error(f"Fallo el procesamiento de {os.path.basename(xls_path)}.")
                    continue
                
                insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                
                logging.info(f"Proceso de ingesta completado con éxito para: {os.path.basename(xls_path)}")

            except Exception as e:
                logging.error(f"Ocurrió un error procesando el archivo {os.path.basename(xls_path)}: {e}")

if __name__ == '__main__':
    main()
