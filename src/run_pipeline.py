import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# -*- coding: utf-8 -*-
"""Script orquestador para ejecutar el pipeline completo de ingesta de datos."""

import subprocess
import logging
import os
from datetime import datetime

# --- Configuración de Logging ---
LOG_FILE = f"pipeline_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

def setup_logging():
    """Configura un logger dual para consola y archivo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def run_script(script_path):
    """
    Ejecuta un script de Python como un subproceso, mostrando su salida en tiempo real.
    Retorna True si el script se ejecuta exitosamente, False en caso contrario.
    """
    logging.info(f"--- INICIANDO SCRIPT: {script_path} ---")
    try:
        # Ejecutar el proceso y dejar que su salida se muestre en la consola principal.
        # `check=True` asegura que se lance una excepción si el script falla.
        subprocess.run(
            ["python", os.path.join(BASE_DIR, script_path)],
            check=True,
            encoding='utf-8'
        )
        logging.info(f"--- SCRIPT {script_path} COMPLETADO EXITOSAMENTE ---\n")
        return True
    except FileNotFoundError:
        logging.error(f"Error: El script {script_path} no fue encontrado.")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"--- SCRIPT {script_path} FALLÓ (código de retorno: {e.returncode}) ---\n")
        return False
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado al ejecutar {script_path}: {e}\n")
        return False

def main():
    """Función principal que orquesta la ejecución del pipeline."""
    setup_logging()
    logging.info("====== INICIANDO PIPELINE DE INGESTA DE DATOS COMPLETO ======")

    # Lista de scripts a ejecutar en orden
    scripts_to_run = [
        # 1. Reseteo y creación de la estructura de la BD
        os.path.join("src", "db", "reset_database.py"),
        
        # 2. Descarga de boletas (requiere login manual)
        os.path.join("src", "ingestion", "download_boletas.py"),

        # 3. Procesamiento de boletas
        os.path.join("src", "ingestion", "process_boletas.py"),
        
        # 4. Ingesta de archivos de Banco Falabella
        os.path.join("src", "ingestion", "ingest_xls_falabella_cc.py"),
        os.path.join("src", "ingestion", "ingest_xls_falabella_cuenta_corriente.py"),
        os.path.join("src", "ingestion", "ingest_xls_falabella_linea_credito.py"),
        
        # 5. Ingesta de archivos de Banco de Chile
        os.path.join("src", "ingestion", "ingest_xls_national_cc.py"),
        os.path.join("src", "ingestion", "ingest_xls_international_cc.py"),
        os.path.join("src", "ingestion", "ingest_pdf_banco_chile_linea_credito.py"),
        os.path.join("src", "ingestion", "ingest_pdf_bank_statement.py")
    ]

    all_successful = True
    for script in scripts_to_run:
        if not run_script(script):
            all_successful = False
            logging.error(f"El pipeline se detuvo debido a un error en {script}.")
            # Si se descomenta la siguiente línea, el pipeline se detendrá al primer error.
            # break 
    
    if all_successful:
        logging.info("====== PIPELINE DE INGESTA COMPLETADO EXITOSAMENTE ======")
    else:
        logging.warning("====== PIPELINE DE INGESTA COMPLETADO CON ERRORES ======")

if __name__ == "__main__":
    main()