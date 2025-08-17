# -*- coding: utf-8 -*-
"""Módulo de configuración central para el proyecto de boletas."""

import os

# --- Directorio Base del Proyecto ---
# Se asume que este archivo está en la raíz del proyecto.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuración de la Base de Datos ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456789',
    'database': 'Boletas'
}

# --- Rutas de Directorios y Archivos ---
# Directorio donde se descargan y se encuentran las boletas en PDF.
BOLETAS_DIR = BASE_DIR

# Archivo de salida para los datos exportados.
EXPORT_CSV_FILE = os.path.join(BASE_DIR, 'boletas_data.csv')

# --- Configuración de Logs ---
# Nombre de los archivos de log para cada script.
DOWNLOAD_LOG_FILE = os.path.join(BASE_DIR, 'download_boletas.log')
PROCESS_LOG_FILE = os.path.join(BASE_DIR, 'process_boletas.log')

# --- URLs ---
MIS_COMPRAS_URL = "https://www.jumbo.cl/mis-compras"
LOGIN_URL = "https://www.jumbo.cl/login"
