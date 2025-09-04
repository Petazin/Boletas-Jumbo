import mysql.connector
from database_utils import db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def execute_sql_from_file(sql_file_path):
    """Ejecuta sentencias SQL desde un archivo en la base de datos."""
    logging.info(f"Intentando ejecutar SQL desde el archivo: {sql_file_path}")
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()

        # Dividir el script en sentencias individuales (asumiendo que están separadas por ';')
        sql_commands = [cmd.strip() for cmd in sql_script.split(';') if cmd.strip()]

        with db_connection() as conn:
            cursor = conn.cursor()
            for command in sql_commands:
                try:
                    logging.info(f"Ejecutando: {command[:75]}...") # Log solo el inicio del comando
                    cursor.execute(command)
                    conn.commit()
                except mysql.connector.Error as err:
                    logging.error(f"Error al ejecutar SQL: {err} en comando: {command[:100]}...")
                    # Dependiendo de la severidad, podrías querer hacer un rollback o re-lanzar
                    conn.rollback() # Rollback en caso de error
                    raise # Re-lanzar para detener el proceso si una tabla no se crea
            logging.info("Todas las sentencias SQL ejecutadas exitosamente.")

    except FileNotFoundError:
        logging.error(f"Error: El archivo SQL no fue encontrado en {sql_file_path}")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado al ejecutar el script SQL: {e}")

if __name__ == "__main__":
    sql_file = r"c:\Users\Petazo\Desktop\Boletas Jumbo\create_staging_tables.sql"
    execute_sql_from_file(sql_file)