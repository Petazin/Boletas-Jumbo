# -*- coding: utf-8 -*-
"""Módulo de configuración central para el proyecto de boletas."""

import os

# --- Directorio Base del Proyecto ---
# Se determina la ruta absoluta del directorio donde se encuentra este archivo (la raíz del proyecto).
# Esto permite que el script funcione correctamente sin importar desde dónde se ejecute.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuración de la Base de Datos ---
# Diccionario con los parámetros de conexión a la base de datos MySQL.
# ¡IMPORTANTE! Modifica estos valores si tu configuración es diferente.
DB_CONFIG = {
    'host': 'localhost',       # Dirección del servidor de la base de datos
    'user': 'root',            # Usuario de la base de datos
    'password': '123456789',   # Contraseña del usuario
    'database': 'Boletas',       # Nombre de la base de datos a la que se conectará
    'allow_public_key_retrieval': True # Opción para permitir la recuperación de la clave pública
}

# --- Rutas de Directorios y Archivos ---

# Directorio donde se descargan y se buscan las boletas en formato PDF.
# Por defecto, es el mismo directorio donde está el proyecto.
BOLETAS_DIR = BASE_DIR

# Nombre y ruta del archivo CSV que se generará con los datos exportados.
EXPORT_CSV_FILE = os.path.join(BASE_DIR, 'boletas_data.csv')

# --- Configuración de Logs ---
# Define las rutas completas para los archivos de registro de cada script.
# Esto ayuda a mantener un registro separado de lo que hace cada proceso.
DOWNLOAD_LOG_FILE = os.path.join(BASE_DIR, 'download_boletas.log')
PROCESS_LOG_FILE = os.path.join(BASE_DIR, 'process_boletas.log')

# --- URLs ---
# URLs utilizadas por el script de descarga (Selenium).
MIS_COMPRAS_URL = "https://www.jumbo.cl/mis-compras"
LOGIN_URL = "https://www.jumbo.cl/login"