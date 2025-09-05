import logging
import mysql.connector
import copy
import os
import sys

# Añadir el directorio base del proyecto al sys.path para que las importaciones funcionen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database_utils import db_connection
from config import DB_CONFIG  # Importar directamente desde config
from alter_table import reset_and_setup_bank_tables
from setup_linea_credito_table import setup_linea_credito_table

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def execute_sql_from_file(cursor, file_path):
    """Lee y ejecuta un script SQL desde un archivo."""
    logging.info(f"Ejecutando script SQL desde: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        # Usamos split(';') para manejar múltiples sentencias, eliminando las vacías
        sql_commands = [cmd.strip() for cmd in f.read().split(';') if cmd.strip()]
        for command in sql_commands:
            try:
                cursor.execute(command)
            except mysql.connector.Error as err:
                logging.error(f"Error ejecutando comando: {command}\n{err}")
                raise

def main():
    """
    Orquesta el reseteo completo de la base de datos.
    ADVERTENCIA: Esta operación es destructiva.
    """
    logging.warning("--- INICIANDO RESETEO COMPLETO DE LA BASE DE DATOS ---")
    
    try:
        # Copiamos la configuración para no modificar el original
        config = copy.deepcopy(DB_CONFIG)
        db_name = config.pop('database')

        # Conexión sin base de datos específica para poder borrarla y crearla
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        logging.info(f"Eliminando la base de datos '{db_name}' si existe...")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        
        logging.info(f"Creando la base de datos '{db_name}'...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        
        cursor.close()
        conn.close()
        
        # Ahora nos conectamos a la base de datos recién creada
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Crear todas las tablas desde el script base
            execute_sql_from_file(cursor, 'create_new_tables.sql')
            logging.info("Tablas base creadas exitosamente.")

            # 2. Crear las tablas de staging
            execute_sql_from_file(cursor, 'create_staging_tables.sql')
            logging.info("Tablas de staging creadas exitosamente.")
            
            # 3. Crear la tabla de mapeo de abonos
            execute_sql_from_file(cursor, 'create_abonos_mapping_table.sql')
            conn.commit()  # Asegurar que el INSERT se guarde
            logging.info("Tabla de mapeo de abonos creada y poblada exitosamente.")
            
        # 4. Ejecutar la lógica de alter_table.py
        # Esta función se conecta por su cuenta
        logging.info("Ejecutando lógica de 'alter_table.py'...")
        reset_and_setup_bank_tables()
        logging.info("Lógica de 'alter_table.py' completada.")

        # 5. Ejecutar la lógica de setup_linea_credito_table.py
        # Esta función también es autónoma
        logging.info("Ejecutando lógica de 'setup_linea_credito_table.py'...")
        setup_linea_credito_table()
        logging.info("Lógica de 'setup_linea_credito_table.py' completada.")

        logging.info("--- RESETEO DE LA BASE DE DATOS COMPLETADO EXITOSAMENTE ---")

    except mysql.connector.Error as err:
        logging.error(f"Ocurrió un error de base de datos durante el reseteo: {err}")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante el reseteo: {e}", exc_info=True)

if __name__ == '__main__':
    main()