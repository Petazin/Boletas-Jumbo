import pandas as pd
import mysql.connector
import logging
import os

from config import DB_CONFIG
from database_utils import db_connection

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_or_create_source_id(cursor, source_name, source_type):
    """Obtiene el source_id si existe, o lo crea si no."""
    query = "SELECT source_id FROM sources WHERE source_name = %s"
    cursor.execute(query, (source_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        insert_query = "INSERT INTO sources (source_name, source_type) VALUES (%s, %s)"
        cursor.execute(insert_query, (source_name, source_type))
        return cursor.lastrowid

def parse_bank_account_statement_xls(file_path, source_name, source_type):
    """
    Parsea un archivo XLS de cartola de cuenta corriente/línea de crédito
    y lo inserta en las tablas _raw.
    """
    logging.info(f"Iniciando el parseo de la cartola bancaria: {file_path}")
    try:
        # Leer el archivo XLS
        # Asumimos que los datos de transacciones comienzan en la fila 10 (índice 9)
        # y que los metadatos están en las primeras filas.
        df = pd.read_excel(file_path, header=None)
        logging.info("Contenido inicial del DataFrame (primeras 20 filas, 10 columnas):")
        logging.info(df.iloc[0:20, 0:10].to_string())

        with db_connection() as conn:
            cursor = conn.cursor()
            source_id = get_or_create_source_id(cursor, source_name, source_type)
            conn.commit() # Commit the source creation

            # --- Extracción de Metadatos ---
            metadata = {}
            # Función auxiliar para manejar valores NaN
            def get_value(df_iloc_result):
                return None if pd.isna(df_iloc_result) else df_iloc_result

            # Ejemplo de extracción de metadatos (ajustar según la estructura real del XLS)
            df = pd.read_excel(file_path, header=None)
        logging.info("Contenido inicial del DataFrame (primeras 20 filas, 10 columnas):")
        logging.info(df.iloc[0:20, 0:10].to_string())

        with db_connection() as conn:
            cursor = conn.cursor()
            source_id = get_or_create_source_id(cursor, source_name, source_type)
            conn.commit() # Commit the source creation

            # --- Extracción de Metadatos ---
            metadata = {}
            # Función auxiliar para manejar valores NaN
            def get_value(df_iloc_result):
                return None if pd.isna(df_iloc_result) else df_iloc_result

            # Ejemplo de extracción de metadatos (ajustar según la estructura real del XLS)
            metadata['account_holder_name'] = get_value(df.iloc[7, 2]) # Sr(a):
            metadata['rut'] = get_value(df.iloc[8, 2]) # Rut:
            metadata['account_number'] = get_value(df.iloc[9, 2]) # Cuenta:
            metadata['currency'] = get_value(df.iloc[10, 2]) # Moneda:
            metadata['statement_issue_date'] = get_value(df.iloc[13, 4]) # Fecha de Emisión
            metadata['statement_folio'] = get_value(df.iloc[16, 0]) # Folio Cartola
            metadata['accounting_balance'] = get_value(df.iloc[16, 1]) # Saldo Contable
            metadata['retentions_24hrs'] = get_value(df.iloc[16, 2]) # Retenciones 24 Hrs.
            metadata['retentions_48hrs'] = get_value(df.iloc[16, 3]) # Retenciones 48 Hrs.
            metadata['initial_balance'] = get_value(df.iloc[19, 0]) # Saldo Inicial
            metadata['available_balance'] = get_value(df.iloc[19, 1]) # Saldo Disponible
            metadata['credit_line_amount'] = get_value(df.iloc[19, 2]) # Línea de Crédito

            # Insertar metadatos en bank_statement_metadata_raw
            insert_metadata_query = """
            INSERT INTO bank_statement_metadata_raw (
                source_id, account_holder_name, rut, account_number, currency,
                statement_issue_date, statement_folio, accounting_balance,
                retentions_24hrs, retentions_48hrs, initial_balance,
                available_balance, credit_line_amount, original_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            metadata_values = (
                source_id, metadata['account_holder_name'], metadata['rut'],
                metadata['account_number'], metadata.get('currency'),
                metadata['statement_issue_date'], metadata['statement_folio'],
                metadata['accounting_balance'], metadata['retentions_24hrs'],
                metadata['retentions_48hrs'], metadata['initial_balance'],
                metadata['available_balance'], metadata['credit_line_amount'],
                os.path.basename(file_path)
            )
            cursor.execute(insert_metadata_query, metadata_values)
            metadata_id = cursor.lastrowid
            conn.commit()
            logging.info(f"Metadatos de cartola insertados con metadata_id: {metadata_id}")

            # --- Extracción de Transacciones ---
            # Asumimos que las transacciones comienzan en la fila 13 (índice 12)
            # y que los encabezados de las columnas están en la fila 12 (índice 11)
            transactions_df = pd.read_excel(file_path, header=11) # header=11 para usar la fila "Fecha", "Descripción", etc. como encabezado

            # Eliminar filas completamente vacías que pandas pueda haber leído
            transactions_df.dropna(how='all', inplace=True)

            # Renombrar columnas para que coincidan con el esquema de la BD
            transactions_df.rename(columns={
                'Fecha': 'transaction_date_str',
                'Descripción': 'transaction_description',
                'Canal o Sucursal': 'channel_or_branch',
                'Cargos (PESOS)': 'charges_pesos',
                'Abonos (PESOS)': 'credits_pesos',
                'Saldo (PESOS)': 'balance_pesos'
            }, inplace=True)

            # Insertar transacciones en bank_account_transactions_raw
            insert_transaction_query = """
            INSERT INTO bank_account_transactions_raw (
                source_id, metadata_id, transaction_date_str, transaction_description,
                channel_or_branch, charges_pesos, credits_pesos, balance_pesos,
                original_line_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            for index, row in transactions_df.iterrows():
                # Convertir NaN a None para la base de datos
                charges = None if pd.isna(row['charges_pesos']) else row['charges_pesos']
                credits = None if pd.isna(row['credits_pesos']) else row['credits_pesos']
                balance = None if pd.isna(row['balance_pesos']) else row['balance_pesos']

                # Reconstruir original_line_data si es necesario, o usar una representación de la fila
                original_line = str(row.to_dict()) # Simple representación de la fila

                transaction_values = (
                    source_id, metadata_id, row['transaction_date_str'], row['transaction_description'],
                    row['channel_or_branch'], charges, credits, balance,
                    original_line
                )
                cursor.execute(insert_transaction_query, transaction_values)
            conn.commit()
            logging.info(f"Transacciones de cartola insertadas exitosamente para metadata_id: {metadata_id}")

    except FileNotFoundError:
        logging.error(f"Error: El archivo no fue encontrado en {file_path}")
    except pd.errors.EmptyDataError:
        logging.error(f"Error: El archivo XLS está vacío o no tiene el formato esperado: {file_path}")
    except Exception as e:
        logging.error(f"Ocurrió un error al procesar el archivo {file_path}: {e}")

if __name__ == "__main__":
    # Ejemplo de uso (esto se orquestaría desde otro script principal)
    # Asegúrate de que el archivo exista y la ruta sea correcta
    sample_file_path = r"c:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\cuenta corriente\cartola_31072025.xls"
    sample_source_name = "Banco de Chile - Cuenta Corriente"
    sample_source_type = "Banco"
    parse_bank_account_statement_xls(sample_file_path, sample_source_name, sample_source_type)
