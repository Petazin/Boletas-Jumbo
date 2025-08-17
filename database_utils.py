# -*- coding: utf-8 -*-
"""Utilidades para la gestión de la conexión a la base de datos."""

import logging
import mysql.connector
from contextlib import contextmanager
from config import DB_CONFIG

@contextmanager
def db_connection():
    """Gestiona la conexión a la base de datos como un manejador de contexto.
    
    Abre una conexión al entrar al bloque y se asegura de que se cierre
    correctamente al salir, incluso si ocurren errores.

    Yields:
        mysql.connector.connection: El objeto de conexión a la base de datos.
    """
    conn = None
    try:
        logging.info(f"Abriendo conexión a la base de datos '{DB_CONFIG.get('database')}'...")
        conn = mysql.connector.connect(**DB_CONFIG)
        yield conn
    except mysql.connector.Error as err:
        logging.error(f"Error de base de datos: {err}")
        # Propagar la excepción para que el código que llama pueda manejarla si es necesario
        raise
    finally:
        if conn and conn.is_connected():
            logging.info("Cerrando conexión a la base de datos.")
            conn.close()
