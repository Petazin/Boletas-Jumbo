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
        logging.info(
            f"Abriendo conexión a la base de datos '{DB_CONFIG.get('database')}'..."
        )
        conn = mysql.connector.connect(**DB_CONFIG)
        yield conn
    except mysql.connector.Error as err:
        logging.error(f"Error de base de datos: {err}")
        raise
    finally:
        if conn and conn.is_connected():
            logging.info("Cerrando conexión a la base de datos.")
            conn.close()





def get_downloaded_order_ids():
    """Obtiene una lista de todos los order_id de la tabla 'historial_descargas'.

    Returns:
        list: Una lista de strings, donde cada string es un order_id.
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT order_id FROM historial_descargas"
        cursor.execute(query)
        return [item[0] for item in cursor.fetchall()]


def insert_download_history(
    order_id,
    fuente,
    fecha_compra,
    fecha_descarga,
    nombre_archivo_original,
    nuevo_nombre_archivo,
    ruta_archivo,
    monto_total,
    cantidad_items,
    estado,
    file_hash,
):
    """Inserta un nuevo registro en la tabla 'historial_descargas'.

    Args:
        order_id (str): El ID del pedido.
        fuente (str): La fuente de la descarga (ej. 'Jumbo').
        fecha_compra (date): La fecha de la compra.
        fecha_descarga (datetime): La fecha y hora de la descarga.
        nombre_archivo_original (str): El nombre original del archivo descargado.
        nuevo_nombre_archivo (str): El nuevo nombre del archivo.
        ruta_archivo (str): La ruta completa del archivo guardado.
        monto_total (float): El monto total de la boleta.
        cantidad_items (int): El número de productos en la boleta.
        estado (str): El estado del procesamiento (ej. 'Descargado').
        file_hash (str): El hash SHA-256 del archivo.
    """
    with db_connection() as conn:
        cursor = conn.cursor()
        query = """
        INSERT INTO historial_descargas (
            order_id, fuente, fecha_compra, fecha_descarga, nombre_archivo_original,
            nuevo_nombre_archivo, ruta_archivo, monto_total, cantidad_items, estado, file_hash
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            order_id,
            fuente,
            fecha_compra,
            fecha_descarga,
            nombre_archivo_original,
            nuevo_nombre_archivo,
            ruta_archivo,
            monto_total,
            cantidad_items,
            estado,
            file_hash,
        )
        cursor.execute(query, values)
        conn.commit()
        logging.info(f"Registro de descarga para el pedido {order_id} guardado.")
