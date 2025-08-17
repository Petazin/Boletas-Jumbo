# -*- coding: utf-8 -*-
"""Utilidades para la gestión de la conexión a la base de datos."""

import logging
import mysql.connector
from contextlib import contextmanager
from config import DB_CONFIG

@contextmanager
def db_connection():
    """Gestiona la conexión a la base de datos como un manejador de contexto.
    
    Esta función asegura que la conexión a la base de datos se abra y se cierre
    de forma segura y automática. El bloque `try...finally` garantiza que la
    conexión siempre se cierre, incluso si ocurren errores durante las operaciones.

    Yields:
        conn (mysql.connector.connection): El objeto de conexión a la base de datos.
                                           Este es el objeto que se usa para crear cursores
                                           y ejecutar consultas.
    """
    conn = None  # Inicializar la variable de conexión
    try:
        # Informar que se está intentando abrir la conexión
        logging.info(f"Abriendo conexión a la base de datos '{DB_CONFIG.get('database')}'...")
        
        # Establecer la conexión usando los parámetros del archivo config.py
        conn = mysql.connector.connect(**DB_CONFIG)
        
        # `yield` cede el control y entrega el objeto de conexión al bloque `with`
        yield conn
        
    except mysql.connector.Error as err:
        # Si ocurre un error específico de MySQL (ej. credenciales incorrectas, DB no existe)
        logging.error(f"Error de base de datos: {err}")
        # Volver a lanzar la excepción para que el script que llamó a esta función sepa del error
        raise
    finally:
        # Este bloque se ejecuta siempre, haya o no haya habido un error.
        if conn and conn.is_connected():
            # Si la conexión se estableció y sigue abierta, cerrarla.
            logging.info("Cerrando conexión a la base de datos.")
            conn.close()