import logging
import mysql.connector
import copy
import os
import sys

# Añadir el directorio base del proyecto al sys.path para que las importaciones funcionen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database_utils import db_connection
from config import DB_CONFIG  # Importar directamente desde config

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def execute_sql_from_file(cursor, file_path):
    """Lee y ejecuta un script SQL desde un archivo."""
    logging.info(f"Ejecutando script SQL desde: {file_path}")
    # Construir la ruta absoluta al archivo SQL
    # Se asume que el script se ejecuta desde el directorio raíz del proyecto
    sql_file_path = os.path.join(os.path.dirname(__file__), '..', '..', file_path)
    with open(sql_file_path, 'r', encoding='utf-8') as f:
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
            
            # Crear todas las tablas desde el script consolidado
            execute_sql_from_file(cursor, 'create_new_tables.sql')
            conn.commit()
            logging.info("Todas las tablas han sido creadas desde 'create_new_tables.sql'.")

        logging.info("--- RESETEO DE LA BASE DE DATOS COMPLETADO EXITOSAMENTE ---")

    except mysql.connector.Error as err:
        logging.error(f"Ocurrió un error de base de datos durante el reseteo: {err}")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante el reseteo: {e}", exc_info=True)

if __name__ == '__main__':
    main()
