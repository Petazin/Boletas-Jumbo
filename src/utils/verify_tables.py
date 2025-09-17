import mysql.connector
from database_utils import db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify_table_creation():
    """Verifica la creación de tablas en la base de datos."""
    logging.info("Verificando la creación de tablas...")
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            logging.info("Tablas encontradas en la base de datos:")
            for table in tables:
                logging.info(f"- {table[0]}")
            return tables
    except Exception as e:
        logging.error(f"Ocurrió un error al verificar las tablas: {e}")
        return None

if __name__ == "__main__":
    verify_table_creation()
