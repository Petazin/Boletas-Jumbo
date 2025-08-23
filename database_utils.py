# -*- coding: utf-8 -*-
"""Utilidades para la gestión de la conexión a la base de datos."""

import logging
import mysql.connector
from contextlib import contextmanager
from config import DB_CONFIG

@contextmanager
def db_connection():
    """Gestiona la conexión a la base de datos como un manejador de contexto."""
    conn = None
    try:
        logging.info(f"Abriendo conexión a la base de datos '{DB_CONFIG.get('database')}'...")
        conn = mysql.connector.connect(**DB_CONFIG)
        yield conn
    except mysql.connector.Error as err:
        logging.error(f"Error de base de datos: {err}")
        raise
    finally:
        if conn and conn.is_connected():
            logging.info("Cerrando conexión a la base de datos.")
            conn.close()

def create_download_history_table():
    """Crea la tabla 'download_history' si no existe.
    
    Esta tabla es fundamental para llevar un registro de todos los archivos descargados,
    evitar duplicados y gestionar el estado del procesamiento.
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        query = """
        CREATE TABLE IF NOT EXISTS download_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id VARCHAR(255) NOT NULL UNIQUE,
            source VARCHAR(50) NOT NULL,
            purchase_date DATE,
            download_date DATETIME NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            new_filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(512) NOT NULL,
            total_amount DECIMAL(10, 2),
            item_count INT,
            status VARCHAR(50) NOT NULL DEFAULT 'Downloaded'
        )
        """
        cursor.execute(query)
        conn.commit()
        logging.info("Tabla 'download_history' asegurada.")

def get_downloaded_order_ids():
    """Obtiene una lista de todos los order_id de la tabla 'download_history'.

    Returns:
        list: Una lista de strings, donde cada string es un order_id.
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT order_id FROM download_history"
        cursor.execute(query)
        return [item[0] for item in cursor.fetchall()]

def insert_download_history(order_id, source, purchase_date, download_date, original_filename, new_filename, file_path, total_amount, item_count, status):
    """Inserta un nuevo registro en la tabla 'download_history'.

    Args:
        order_id (str): El ID del pedido.
        source (str): La fuente de la descarga (ej. 'Jumbo').
        purchase_date (date): La fecha de la compra.
        download_date (datetime): La fecha y hora de la descarga.
        original_filename (str): El nombre original del archivo descargado.
        new_filename (str): El nuevo nombre del archivo.
        file_path (str): La ruta completa del archivo guardado.
        total_amount (float): El monto total de la boleta.
        item_count (int): El número de productos en la boleta.
        status (str): El estado del procesamiento (ej. 'Downloaded').
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        query = """
        INSERT INTO download_history 
        (order_id, source, purchase_date, download_date, original_filename, new_filename, file_path, total_amount, item_count, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (order_id, source, purchase_date, download_date, original_filename, new_filename, file_path, total_amount, item_count, status)
        cursor.execute(query, values)
        conn.commit()
        logging.info(f"Registro de descarga para el pedido {order_id} guardado.")