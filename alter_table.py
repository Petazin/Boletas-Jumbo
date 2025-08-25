import mysql.connector
from database_utils import db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def alter_table_currency_column():
    """Altera la columna 'currency' en bank_statement_metadata_raw a VARCHAR(20)."""
    logging.info("Intentando alterar la tabla bank_statement_metadata_raw...")
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            alter_query = "ALTER TABLE bank_statement_metadata_raw MODIFY COLUMN currency VARCHAR(20);"
            cursor.execute(alter_query)
            conn.commit()
            logging.info("Columna 'currency' alterada exitosamente a VARCHAR(20).")
    except Exception as e:
        logging.error(f"Ocurrió un error al alterar la tabla: {e}")

if __name__ == "__main__":
    alter_table_currency_column()
