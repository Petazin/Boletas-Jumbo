# -*- coding: utf-8 -*-
"""Módulo de configuración central para el proyecto de boletas."""

import os

# --- Directorio Base del Proyecto ---
# Se determina la ruta absoluta del directorio donde se encuentra este
# archivo (la raíz del proyecto).
# Esto permite que el script funcione correctamente sin importar desde dónde se ejecute.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuración de la Base de Datos ---
# Diccionario con los parámetros de conexión a la base de datos MySQL.
# ¡IMPORTANTE! Modifica estos valores si tu configuración es diferente.
DB_CONFIG = {
    "host": "localhost",  # Dirección del servidor de la base de datos
    "user": "root",  # Usuario de la base de datos
    "password": "123456789",  # Contraseña del usuario
    "database": "Boletas",  # Nombre de la base de datos a la que se conectará
    # Usar un plugin de autenticación más compatible
    "auth_plugin": "mysql_native_password",
}

# --- Rutas de Directorios y Archivos ---

# Directorio donde se descargan temporalmente las boletas antes de ser procesadas.
# Usado por Selenium para guardar los archivos con su nombre original.
DOWNLOADS_DIR = BASE_DIR

# Directorio donde se almacenarán las boletas organizadas por fuente.
ORGANIZED_DIR = os.path.join(BASE_DIR, "descargas", "Jumbo")

# Directorio donde se moverán los PDFs que no puedan ser procesados correctamente.
QUARANTINE_DIR = os.path.join(BASE_DIR, "cuarentena_pdfs")

# Fuente de datos actual
CURRENT_SOURCE = "Jumbo"



# Nombre y ruta del archivo CSV que se generará con los datos exportados.
EXPORT_CSV_FILE = os.path.join(BASE_DIR, "boletas_data.csv")

# --- Configuración de Logs ---
# Define las rutas completas para los archivos de registro de cada script.
# Esto ayuda a mantener un registro separado de lo que hace cada proceso.
DOWNLOAD_LOG_FILE = os.path.join(BASE_DIR, "download_boletas.log")
PROCESS_LOG_FILE = os.path.join(BASE_DIR, "process_boletas.log")

# --- URLs ---
# URLs utilizadas por el script de descarga (Selenium).
MIS_COMPRAS_URL = "https://www.jumbo.cl/mis-compras"
LOGIN_URL = "https://www.jumbo.cl/login"

# --- Patrones de Expresiones Regulares (Regex) ---
# Centralización de patrones regex utilizados para la extracción de datos de PDFs.
REGEX_PATTERNS = {
    "BOLETA_NUMERO": r"BOLETA\s*ELECTRONICA\s*N\D*(\d+)",
    "FECHA_HORA": r"FECHA\s+HORA LOCAL.*?(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})",
    "SALDO_PUNTOS": r"SALDO\s+DE\s+PUNTOS\s+AL\s*(\d{2}[-/]\d{2}[-/]\d{4})",
    "NOMBRE_ARCHIVO_PDF": r"v\d+jmch-\d+_(\d{13})\.pdf",
    "PRODUCTO": r"^\s*(\d{8,13})\s+(.+?)\s+([\d.,]+)\s*$",
    "CANTIDAD_PRECIO": r"^\s*(\d+)\s*X\s*\$([\d.,]+)",
    "OFERTA_DESCUENTO": r"(TMP\s*(?:OFERTA|DESCUENTO).*?)(-?[\d.,]+)\s*$",
}
