import pandas as pd
import mysql.connector
import logging
import os
from datetime import datetime

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

def find_cell_by_keyword(df, keyword, start_row=0, end_row=None, start_col=0, end_col=None):
    """
    Busca una palabra clave en un DataFrame y devuelve la fila y columna de la primera ocurrencia.
    """
    if end_row is None: end_row = df.shape[0]
    if end_col is None: end_col = df.shape[1]

    for r in range(start_row, end_row):
        for c in range(start_col, end_col):
            cell_value = df.iloc[r, c]
            if isinstance(cell_value, str) and keyword in cell_value:
                return r, c
    return None, None

def get_value_from_relative_position(df, base_row, base_col, row_offset, col_offset):
    """
    Obtiene un valor de una celda en relación a una posición base.
    """
    target_row, target_col = base_row + row_offset, base_col + col_offset
    if 0 <= target_row < df.shape[0] and 0 <= target_col < df.shape[1]:
        value = df.iloc[target_row, target_col]
        return None if pd.isna(value) else value
    return None

def parse_date_string(date_str):
    """
    Intenta parsear una cadena de fecha en formato DD/MM/YYYY y la devuelve como YYYY-MM-DD.
    """
    if pd.isna(date_str) or not isinstance(date_str, str): return None
    try:
        # Eliminar espacios en blanco y luego parsear
        return datetime.strptime(date_str.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        logging.warning(f"No se pudo parsear la fecha: {date_str}")
        return None

def parse_bank_account_statement_xls(file_path, source_name, source_type):
    """
    Parsea un archivo XLS de cartola de cuenta corriente/línea de crédito
    y lo inserta en las tablas _raw.
    """
    logging.info(f"Iniciando el parseo de la cartola bancaria: {file_path}")
    try:
        df = pd.read_excel(file_path, header=None)
        logging.info("Contenido inicial del DataFrame (primeras 20 filas, 10 columnas):")
        logging.info(df.iloc[0:20, 0:10].to_string())

        with db_connection() as conn:
            cursor = conn.cursor()
            source_id = get_or_create_source_id(cursor, source_name, source_type)
            conn.commit() # Commit the source creation

            # --- Extracción de Metadatos ---
            metadata = {}

            # Buscar y extraer metadatos de forma robusta
            # Sr(a):
            row, col = find_cell_by_keyword(df, "Sr(a):", end_row=10)
            if row is not None: metadata['account_holder_name'] = get_value_from_relative_position(df, row, col, 0, 1)

            # Rut:
            row, col = find_cell_by_keyword(df, "Rut:", end_row=10)
            if row is not None: metadata['rut'] = get_value_from_relative_position(df, row, col, 0, 1)

            # Cuenta:
            row, col = find_cell_by_keyword(df, "Cuenta:", end_row=10)
            if row is not None: metadata['account_number'] = get_value_from_relative_position(df, row, col, 0, 1)

            # Moneda:
            row, col = find_cell_by_keyword(df, "Moneda:", end_row=10)
            if row is not None: metadata['currency'] = get_value_from_relative_position(df, row, col, 0, 1)

            # Fecha de Emisión
            row, col = find_cell_by_keyword(df, "Fecha de Emisión", end_row=15)
            if row is not None: metadata['statement_issue_date'] = parse_date_string(get_value_from_relative_position(df, row, col, 0, 1))

            # Folio Cartola
            row, col = find_cell_by_keyword(df, "Folio Cartola", end_row=20)
            if row is not None: metadata['statement_folio'] = get_value_from_relative_position(df, row, col, 1, 0)

            # Saldo Contable
            row, col = find_cell_by_keyword(df, "Saldo Contable", end_row=20)
            if row is not None: metadata['accounting_balance'] = get_value_from_relative_position(df, row, col, 1, 0)

            # Retenciones 24 Hrs.
            row, col = find_cell_by_keyword(df, "Retenciones 24 Hrs.", end_row=20)
            if row is not None: metadata['retentions_24hrs'] = get_value_from_relative_position(df, row, col, 1, 0)

            # Retenciones 48 Hrs.
            row, col = find_cell_by_keyword(df, "Retenciones 48 Hrs.", end_row=20)
            if row is not None: metadata['retentions_48hrs'] = get_value_from_relative_position(df, row, col, 1, 0)

            # Saldo Inicial (en la sección de saldos)
            row, col = find_cell_by_keyword(df, "Saldo Inicial", start_row=15, end_row=25)
            if row is not None: metadata['initial_balance'] = get_value_from_relative_position(df, row, col, 1, 0)

            # Saldo Disponible
            row, col = find_cell_by_keyword(df, "Saldo Disponible", start_row=15, end_row=25)
            if row is not None: metadata['available_balance'] = get_value_from_relative_position(df, row, col, 1, 0)

            # Línea de Crédito
            row, col = find_cell_by_keyword(df, "Línea de Crédito", start_row=15, end_row=25)
            if row is not None: metadata['credit_line_amount'] = get_value_from_relative_position(df, row, col, 1, 0)

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
                source_id, metadata.get('account_holder_name'), metadata.get('rut'),
                metadata.get('account_number'), metadata.get('currency'),
                metadata.get('statement_issue_date'), metadata.get('statement_folio'),
                metadata.get('accounting_balance'), metadata.get('retentions_24hrs'),
                metadata.get('retentions_48hrs'), metadata.get('initial_balance'),
                metadata.get('available_balance'), metadata.get('credit_line_amount'),
                os.path.basename(file_path)
            )
            cursor.execute(insert_metadata_query, metadata_values)
            metadata_id = cursor.lastrowid
            conn.commit()
            logging.info(f"Metadatos de cartola insertados con metadata_id: {metadata_id}")

            # --- Extracción de Transacciones ---
            # Buscar la fila de encabezado de transacciones
            header_row, _ = find_cell_by_keyword(df, "Fecha", start_row=20, end_row=30) # Buscar "Fecha" en un rango razonable

            if header_row is not None:
                # Leer el archivo sin encabezado inicialmente
                transactions_df = pd.read_excel(file_path, header=None)

                # Extraer los nombres de las columnas de la fila de encabezado
                # y limpiar los nombres (convertir a string, manejar NaN)
                column_names = [str(x).strip() if pd.notna(x) else f"Unnamed_{i}" for i, x in enumerate(transactions_df.iloc[header_row])]
                transactions_df.columns = column_names

                # Eliminar las filas anteriores al encabezado
                transactions_df = transactions_df[header_row+1:].reset_index(drop=True)

                # Eliminar filas completamente vacías que pandas pueda haber leído
                transactions_df.dropna(how='all', inplace=True)

                # Eliminar la columna 'Unnamed_0' si existe, ya que no es relevante para la base de datos
                if 'Unnamed_0' in transactions_df.columns:
                    transactions_df.drop(columns=['Unnamed_0'], inplace=True)

                # Renombrar columnas para que coincidan con el esquema de la BD
                transactions_df.rename(columns={
                    'Fecha': 'transaction_date_str',
                    'Descripción': 'transaction_description',
                    'Canal o Sucursal': 'channel_or_branch',
                    'Cargos (PESOS)': 'charges_pesos',
                    'Abonos (PESOS)': 'credits_pesos',
                    'Saldo (PESOS)': 'balance_pesos'
                }, inplace=True)

                logging.info(f"Columnas de transactions_df después de renombrar y antes de la selección final: {transactions_df.columns.tolist()}")

                # Seleccionar solo las columnas relevantes para la inserción
                expected_columns = [
                    'transaction_date_str', 'transaction_description', 'channel_or_branch',
                    'charges_pesos', 'credits_pesos', 'balance_pesos'
                ]
                # Asegurarse de que solo las columnas esperadas estén presentes, eliminando cualquier otra
                transactions_df = transactions_df[expected_columns].copy()

                # Insertar transacciones en bank_account_transactions_raw
                insert_transaction_query = """
                INSERT INTO bank_account_transactions_raw (
                    source_id, metadata_id, transaction_date_str, transaction_description,
                    channel_or_branch, charges_pesos, credits_pesos, balance_pesos, original_line_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                for index, row in transactions_df.iterrows():
                    # Convertir NaN a 0.0 para la base de datos (para depuración de error 'nan')
                    charges = 0.0 if pd.isna(row['charges_pesos']) else row['charges_pesos']
                    credits = 0.0 if pd.isna(row['credits_pesos']) else row['credits_pesos']
                    balance = 0.0 if pd.isna(row['balance_pesos']) else row['balance_pesos']

                    # Reconstruir original_line_data: convertir NaN a None para evitar problemas
                    row_dict = row.to_dict()
                    cleaned_row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                    # original_line = str(cleaned_row_dict) # Simple representación de la fila
                    original_line = "TEST_DATA" # Temporalmente para depuración

                    transaction_values = (
                        source_id, metadata_id, row['transaction_date_str'], row['transaction_description'],
                        row['channel_or_branch'], charges, credits, balance, original_line
                    )
                    cursor.execute(insert_transaction_query, transaction_values)
                conn.commit()
                logging.info(f"Transacciones de cartola insertadas exitosamente para metadata_id: {metadata_id}")
            else:
                logging.warning(f"No se encontró la fila de encabezado de transacciones en {file_path}")

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
