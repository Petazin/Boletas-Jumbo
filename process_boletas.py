# -*- coding: utf-8 -*-
"""Script orquestador para procesar los archivos PDF de boletas.""" 

import logging
import os
import mysql.connector
import multiprocessing
import shutil
import hashlib

# Importar módulos y configuración del proyecto
from config import PROCESS_LOG_FILE
from database_utils import db_connection
from pdf_parser import process_pdf
from utils.file_utils import log_file_movement, generate_standardized_filename


# --- CONFIGURACIÓN ---
DOCUMENT_TYPE = 'BOLETA_JUMBO'

# Configuración del logger para el estado de la ingesta
ingestion_status_logger = logging.getLogger('ingestion_status')
ingestion_status_logger.setLevel(logging.INFO)
status_file_handler = logging.FileHandler('ingestion_status.log')
status_formatter = logging.Formatter('%(asctime)s - %(message)s')
status_file_handler.setFormatter(status_formatter)
ingestion_status_logger.addHandler(status_file_handler)

def setup_logging():
    """Configura el sistema de logging para este script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(PROCESS_LOG_FILE, mode="w"),
            logging.StreamHandler(),
        ],
    )

def calculate_file_hash(file_path):
    """Calcula el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def is_file_processed(conn, file_hash):
    """Verifica si un archivo con un hash específico ya ha sido procesado."""
    cursor = conn.cursor(buffered=True)
    query = "SELECT 1 FROM metadatos_cartolas_bancarias_raw WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone() is not None
    cursor.close()
    return result

def get_source_id(conn, source_name='Jumbo'):
    """Obtiene el ID de la fuente, creándolo si no existe."""
    cursor = conn.cursor(buffered=True)
    query = "SELECT fuente_id FROM fuentes WHERE nombre_fuente = %s"
    cursor.execute(query, (source_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        insert_query = "INSERT INTO fuentes (nombre_fuente) VALUES (%s)"
        cursor.execute(insert_query, (source_name,))
        conn.commit()
        return cursor.lastrowid

def insert_metadata(conn, source_id, file_path, file_hash, doc_type_desc):
    """Inserta los metadatos del archivo, incluyendo su hash y tipo de documento."""
    cursor = conn.cursor()
    query = """
    INSERT INTO metadatos_cartolas_bancarias_raw (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type_desc)
    cursor.execute(query, values)
    conn.commit()
    return cursor.lastrowid

def insert_boleta_data_to_staging(cursor, metadata_id, fuente_id, boleta_id, hora_compra, products_data):
    """Inserta una lista de productos de una boleta en la tabla de staging de Jumbo."""
    insert_query = """
    INSERT INTO staging_boletas_jumbo (
        metadata_id, fuente_id, boleta_id, fecha_compra, hora_compra, sku,
        descripcion_producto, precio_total_item_str, cantidad_str,
        precio_unitario_str, descripcion_oferta, monto_descuento_str
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for product in products_data:
        try:
            data_tuple = (
                metadata_id,
                fuente_id,
                boleta_id,
                product["fecha_transaccion"], # Esto es fecha_compra
                hora_compra,
                product["sku"],
                product["descripcion_producto"],
                str(product["precio_total_item"]),
                str(product["cantidad"]),
                str(product["precio_unitario"]),
                product["descripcion_oferta"],
                str(product["monto_descuento"]),
            )
            cursor.execute(insert_query, data_tuple)
        except mysql.connector.Error as err:
            sku = product.get('sku', 'N/A')
            logging.error(
                f"Error al insertar SKU {sku} de boleta {boleta_id} en staging: {err}"
            )

def _process_single_pdf_task(args):
    pdf_path, order_id, file_hash, source_id = args
    try:
        if not os.path.exists(pdf_path):
            return order_id, "Error - File not found", None, None, None, None, None, None

        conn = None # Initialize conn to None
        try:
            conn = db_connection().__enter__() # Get connection from context manager
            metadata_id = insert_metadata(conn, source_id, pdf_path, file_hash, DOCUMENT_TYPE)
            boleta_id, purchase_date, purchase_time, products_data = process_pdf(pdf_path)

            if boleta_id and products_data and purchase_date:
                return order_id, "Processed", boleta_id, purchase_date, purchase_time, products_data, file_hash, metadata_id
            else:
                return order_id, "Error - Parsing failed or date not found", None, None, None, None, None, None
        finally:
            if conn:
                conn.__exit__(None, None, None) # Close connection

    except Exception as e:
        return order_id, f"Error - Unexpected: {e}", None, None, None, None, None, None

def main():
    """Función principal que orquesta el proceso de leer y procesar PDFs."""
    setup_logging()
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            conn.commit()

            source_id = get_source_id(conn, 'Jumbo') # Get Jumbo source_id

            files_to_process = []
            query = "SELECT ruta_archivo, order_id, file_hash FROM historial_descargas WHERE estado = 'Descargado'"
            cursor.execute(query)
            for ruta_archivo, order_id, file_hash in cursor.fetchall():
                files_to_process.append((ruta_archivo, order_id, file_hash, source_id)) # Pass source_id

            file_path_map = {order_id: (file_path, file_hash) for file_path, order_id, file_hash, _ in files_to_process}

            # Use multiprocessing Pool to process PDFs in parallel
            with multiprocessing.Pool() as pool:
                results = pool.imap_unordered(_process_single_pdf_task, files_to_process)

                for order_id, status, boleta_id, purchase_date, purchase_time, products_data, file_hash, metadata_id in results:
                    # Get original filename for logging
                    original_filepath = file_path_map[order_id][0]
                    pdf_file = os.path.basename(original_filepath)

                    if status == "Processed":
                        # Insert into staging table
                        insert_boleta_data_to_staging(
                            cursor,
                            metadata_id,
                            source_id,
                            boleta_id,
                            purchase_time,
                            products_data
                        )
                        conn.commit()
                        msg = f"Datos de {pdf_file} insertados correctamente en staging."
                        logging.info(msg)

                        # Mover el archivo PDF a la carpeta de procesados con nombre estandarizado
                        processed_dir = os.path.join(os.path.dirname(original_filepath), 'procesados')
                        os.makedirs(processed_dir, exist_ok=True)
                        
                        new_filename = generate_standardized_filename(
                            document_type=DOCUMENT_TYPE,
                            document_period=purchase_date, # purchase_date is a datetime object
                            file_hash=file_hash,
                            original_filename=pdf_file
                        )

                        processed_filepath = os.path.join(processed_dir, new_filename)
                        shutil.move(original_filepath, processed_filepath)
                        log_file_movement(original_filepath, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")
                        ingestion_status_logger.info(f"FILE: {new_filename} | HASH: {file_hash} | STATUS: Processed Successfully")

                    else:
                        # No update_status for staging, just log failure
                        msg = (f"No se pudo procesar completamente {pdf_file}. "
                               f"Estado: {status}. Saltando.")
                        logging.warning(msg)
                        log_file_movement(file_path_map[order_id][0], "N/A", "FAILED", f"Error al procesar: {status}")
                        ingestion_status_logger.info(f"FILE: {pdf_file} | HASH: {file_hash} | STATUS: Failed - {status}")

        logging.info("Proceso completado. Revisa tu base de datos MySQL.")

    except mysql.connector.Error:
        logging.error("El script terminó debido a un error con la base de datos.")
        ingestion_status_logger.info(f"GLOBAL_ERROR: Database error occurred.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado en el proceso principal: {e}")
        ingestion_status_logger.info(f"GLOBAL_ERROR: Unexpected error - {e}")


if __name__ == "__main__":
    main()