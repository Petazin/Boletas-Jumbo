import os
import shutil
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Definición de Rutas ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Nueva estructura de directorios
NEW_DIRS = {
    "src": os.path.join(BASE_DIR, 'src'),
    "core": os.path.join(BASE_DIR, 'src', 'core'),
    "db": os.path.join(BASE_DIR, 'src', 'db'),
    "ingestion": os.path.join(BASE_DIR, 'src', 'ingestion'),
    "utils": os.path.join(BASE_DIR, 'src', 'utils'),
    "fuentes": os.path.join(BASE_DIR, 'fuentes'),
    "procesados": os.path.join(BASE_DIR, 'procesados'),
    "cuarentena": os.path.join(BASE_DIR, 'cuarentena'),
    "logs": os.path.join(BASE_DIR, 'logs')
}

# Mapeo de scripts a mover
SCRIPTS_TO_MOVE = {
    # Root a src/core
    'pdf_parser.py': NEW_DIRS['core'],
    'product_categorizer.py': NEW_DIRS['core'],
    # Root a src/db
    'database_utils.py': NEW_DIRS['db'],
    # Root a src/ingestion
    'download_boletas.py': NEW_DIRS['ingestion'],
    'process_boletas.py': NEW_DIRS['ingestion'],
    'ingest_pdf_banco_chile_linea_credito.py': NEW_DIRS['ingestion'],
    'ingest_pdf_bank_statement.py': NEW_DIRS['ingestion'],
    'ingest_xls_falabella_cc.py': NEW_DIRS['ingestion'],
    'ingest_xls_falabella_cuenta_corriente.py': NEW_DIRS['ingestion'],
    'ingest_xls_falabella_linea_credito.py': NEW_DIRS['ingestion'],
    'ingest_xls_international_cc.py': NEW_DIRS['ingestion'],
    'ingest_xls_national_cc.py': NEW_DIRS['ingestion'],
    # Root a src/utils
    'add_transaction_hash_column.py': NEW_DIRS['utils'],
    'alter_table.py': NEW_DIRS['utils'],
    'check_db_query.py': NEW_DIRS['utils'],
    'check_staging_data.py': NEW_DIRS['utils'],
    'clean_test_file.py': NEW_DIRS['utils'],
    'cleanup_fuentes_table.py': NEW_DIRS['utils'],
    'execute_sql_script.py': NEW_DIRS['utils'],
    'execute_staging_sql.py': NEW_DIRS['utils'],
    'inspect_pdf_table.py': NEW_DIRS['utils'],
    'inspect_xls.py': NEW_DIRS['utils'],
    'move_files_back.py': NEW_DIRS['utils'],
    'verify_tables.py': NEW_DIRS['utils'],
    # Root a src/
    'config.py': NEW_DIRS['src'],
    'run_pipeline.py': NEW_DIRS['src'],
    'export_data.py': NEW_DIRS['src'],
    # 'utils' a 'src'
    os.path.join('utils', 'file_utils.py'): NEW_DIRS['utils'],
    os.path.join('utils', 'db', 'reset_database.py'): NEW_DIRS['db'],
}

# Mapeo de directorios de datos
DATA_DIRS_TO_MOVE = {
    os.path.join(BASE_DIR, 'descargas'): NEW_DIRS['fuentes'],
    os.path.join(BASE_DIR, 'archivos_procesados'): NEW_DIRS['procesados'],
    os.path.join(BASE_DIR, 'cuarentena_pdfs'): NEW_DIRS['cuarentena'],
}

# --- Funciones de Migración ---

def create_new_dirs():
    """Crea la nueva estructura de directorios."""
    logging.info("1. Creando nueva estructura de directorios...")
    for name, path in NEW_DIRS.items():
        if not os.path.exists(path):
            os.makedirs(path)
            logging.info(f"Directorio creado: {path}")
        else:
            logging.warning(f"Directorio ya existe: {path}")

def move_scripts():
    """Mueve los scripts a sus nuevas ubicaciones en src/."""
    logging.info("2. Moviendo scripts a la carpeta 'src'...")
    for old_path_rel, new_dir in SCRIPTS_TO_MOVE.items():
        old_path_abs = os.path.join(BASE_DIR, old_path_rel)
        if os.path.exists(old_path_abs):
            try:
                shutil.move(old_path_abs, new_dir)
                logging.info(f"Movido: {old_path_rel} -> {new_dir}")
            except Exception as e:
                logging.error(f"Error moviendo {old_path_rel}: {e}")
        else:
            logging.warning(f"Script no encontrado, omitiendo: {old_path_rel}")

def move_data_dirs():
    """Mueve y renombra los directorios de datos."""
    logging.info("3. Migrando directorios de datos...")
    for old_dir, new_dir in DATA_DIRS_TO_MOVE.items():
        if os.path.exists(old_dir):
            # Mover el contenido de la carpeta antigua a la nueva
            for item in os.listdir(old_dir):
                s = os.path.join(old_dir, item)
                d = os.path.join(new_dir, item)
                try:
                    shutil.move(s, d)
                    logging.info(f"Movido contenido: {s} -> {d}")
                except Exception as e:
                    logging.error(f"Error moviendo {s}: {e}")
            # Eliminar la carpeta antigua vacía
            try:
                os.rmdir(old_dir)
                logging.info(f"Directorio antiguo eliminado: {old_dir}")
            except OSError as e:
                logging.error(f"Error eliminando directorio antiguo {old_dir}: {e}")
        else:
            logging.warning(f"Directorio de datos no encontrado, omitiendo: {old_dir}")

def update_config_file():
    """Actualiza las rutas en el archivo de configuración."""
    logging.info("4. Actualizando 'src/config.py'...")
    config_path = os.path.join(NEW_DIRS['src'], 'config.py')
    if not os.path.exists(config_path):
        logging.error("El archivo config.py no se encontró en src/. No se puede actualizar.")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Reemplazar BASE_DIR para que apunte a la raíz del proyecto, no a 'src'
    content = content.replace(
        "BASE_DIR = os.path.dirname(os.path.abspath(__file__))",
        "BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Apunta a la raíz del proyecto"
    )
    
    # Actualizar rutas específicas
    replacements = {
        'os.path.join(BASE_DIR, "descargas", "Jumbo")': 'os.path.join(BASE_DIR, "fuentes", "retail", "Jumbo")',
        'os.path.join(BASE_DIR, "cuarentena_pdfs")': 'os.path.join(BASE_DIR, "cuarentena")',
        'os.path.join(BASE_DIR, "download_boletas.log")': 'os.path.join(BASE_DIR, "logs", "download_boletas.log")',
        'os.path.join(BASE_DIR, "process_boletas.log")': 'os.path.join(BASE_DIR, "logs", "process_boletas.log")'
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logging.info("'config.py' actualizado exitosamente.")

def update_run_pipeline_file():
    """Actualiza las rutas de los scripts en run_pipeline.py."""
    logging.info("5. Actualizando 'src/run_pipeline.py'...")
    pipeline_path = os.path.join(NEW_DIRS['src'], 'run_pipeline.py')
    if not os.path.exists(pipeline_path):
        logging.error("El archivo run_pipeline.py no se encontró en src/. No se puede actualizar.")
        return

    with open(pipeline_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Actualizar rutas de scripts
    script_path_updates = {
        'os.path.join("utils", "db", "reset_database.py")': 'os.path.join("src", "db", "reset_database.py")',
        '"download_boletas.py"': 'os.path.join("src", "ingestion", "download_boletas.py")',
        '"process_boletas.py"': 'os.path.join("src", "ingestion", "process_boletas.py")',
        '"ingest_xls_falabella_cc.py"': 'os.path.join("src", "ingestion", "ingest_xls_falabella_cc.py")',
        '"ingest_xls_falabella_cuenta_corriente.py"': 'os.path.join("src", "ingestion", "ingest_xls_falabella_cuenta_corriente.py")',
        '"ingest_xls_falabella_linea_credito.py"': 'os.path.join("src", "ingestion", "ingest_xls_falabella_linea_credito.py")',
        '"ingest_xls_national_cc.py"': 'os.path.join("src", "ingestion", "ingest_xls_national_cc.py")',
        '"ingest_xls_international_cc.py"': 'os.path.join("src", "ingestion", "ingest_xls_international_cc.py")',
        '"ingest_pdf_banco_chile_linea_credito.py"': 'os.path.join("src", "ingestion", "ingest_pdf_banco_chile_linea_credito.py")',
        '"ingest_pdf_bank_statement.py"': 'os.path.join("src", "ingestion", "ingest_pdf_bank_statement.py")'
    }

    for old, new in script_path_updates.items():
        content = content.replace(old, new)
        
    # Cambiar la forma en que se ejecuta el subproceso para que funcione desde la raíz
    # Se usan triple comillas para evitar errores con strings multilínea
    old_subprocess_call = '''subprocess.run(
            ["python", script_path],'''
    new_subprocess_call = '''subprocess.run(
            ["python", os.path.join(BASE_DIR, script_path)],'''
    content = content.replace(old_subprocess_call, new_subprocess_call)
    
    # Añadir BASE_DIR al principio del script
    if "BASE_DIR = os.path.dirname(os.path.abspath(__file__))" not in content:
        content = "import os\nBASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n\n" + content


    with open(pipeline_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logging.info("'run_pipeline.py' actualizado exitosamente.")

def cleanup_old_dirs():
    """Elimina los directorios antiguos que ya no se necesitan."""
    logging.info("6. Limpiando directorios antiguos...")
    old_dirs = [
        os.path.join(BASE_DIR, 'utils'),
        os.path.join(BASE_DIR, '__pycache__')
    ]
    for old_dir in old_dirs:
        if os.path.exists(old_dir):
            try:
                shutil.rmtree(old_dir)
                logging.info(f"Directorio eliminado: {old_dir}")
            except OSError as e:
                logging.error(f"Error eliminando {old_dir}: {e}")

def main():
    """Función principal que orquesta la migración."""
    logging.info("====== INICIANDO MIGRACIÓN DE ESTRUCTURA DE PROYECTO ======")
    
    create_new_dirs()
    move_scripts()
    move_data_dirs()
    update_config_file()
    update_run_pipeline_file()
    cleanup_old_dirs()
    
    logging.info("====== MIGRACIÓN COMPLETADA EXITOSAMENTE ======")
    logging.warning("Por favor, revisa los cambios y ejecuta 'python src/run_pipeline.py' para probar el nuevo flujo.")
    logging.info(f"Este script de migración ('{os.path.basename(__file__)}') puede ser eliminado después de verificar que todo funcione.")

if __name__ == "__main__":
    main()