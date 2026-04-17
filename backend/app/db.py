import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Crea y retorna una conexión a la base de datos MySQL."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "db"), # 'db' es el nombre del servicio en docker-compose
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=3306 # Puerto interno del contenedor
        )
        if connection.is_connected():
            return connection
    except Error as e:
        logger.error(f"Error al conectar a MySQL: {e}")
        return None

def get_db():
    """Generador para ser usado como dependencia en FastAPI."""
    db = get_db_connection()
    try:
        yield db
    finally:
        if db and db.is_connected():
            db.close()
