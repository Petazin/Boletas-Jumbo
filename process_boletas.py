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
    # Clear existing handlers to prevent duplicate logs if called multiple times
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
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
    # Temporalmente, siempre devuelve False para forzar el reprocesamiento.
    return False

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
    INSERT INTO raw_metadatos_documentos (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, os.path.basename(file_path), file_hash, doc_type_desc)
    cursor.execute(query, values)
    # Removed conn.commit() here
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

def validate_staging_data_jumbo(conn, metadata_id, expected_count, totals_from_pdf):
    """
    Valida los datos insertados en staging_boletas_jumbo con una lógica de 2 niveles.
    1. Valida la integridad de los items (conteo y suma de subtotales).
    2. Valida la coherencia de los totales de la boleta (subtotal - descuentos = total).
    """
    cursor = conn.cursor()
    try:
        # --- Nivel 1: Validación de Integridad de Items ---

        # 1a. Validar conteo de productos
        cursor.execute("SELECT COUNT(*) FROM staging_boletas_jumbo WHERE metadata_id = %s", (metadata_id,))
        actual_count = cursor.fetchone()[0]
        count_valid = actual_count == expected_count
        logging.info(f"VALIDACIÓN CONTEO: ESPERADO={expected_count}, OBTENIDO={actual_count} -> {'ÉXITO' if count_valid else 'FALLO'}")

        # 1b. Validar suma de precios de productos (integridad de items)
        cursor.execute("SELECT SUM(CAST(precio_total_item_str AS DECIMAL(15,2))) FROM staging_boletas_jumbo WHERE metadata_id = %s", (metadata_id,))
        actual_sum_products = cursor.fetchone()[0] or 0.0
        
        sub_total_pdf = totals_from_pdf['sub_total']
        item_integrity_valid = abs(float(actual_sum_products) - sub_total_pdf) < 0.01
        logging.info(f"VALIDACIÓN INTEGRIDAD ITEMS (SUMA BD vs SUBTOTAL PDF): BD={actual_sum_products}, PDF={sub_total_pdf} -> {'ÉXITO' if item_integrity_valid else 'FALLO'}")

        # --- Nivel 2: Validación de Coherencia de la Boleta ---
        discounts_pdf = totals_from_pdf['discounts']
        total_pdf = totals_from_pdf['total']
        
        receipt_coherence_valid = abs((sub_total_pdf - discounts_pdf) - total_pdf) < 0.01
        logging.info(f"VALIDACIÓN COHERENCIA BOLETA (SUBTOTAL - DCTO vs TOTAL): PDF_CALC={(sub_total_pdf - discounts_pdf)}, PDF_TOTAL={total_pdf} -> {'ÉXITO' if receipt_coherence_valid else 'FALLO'}")

        if not (count_valid and item_integrity_valid and receipt_coherence_valid):
            return False
        
        return True

    except Exception as e:
        logging.error(f"Error durante la validación de staging de Jumbo: {e}", exc_info=True)
        return False
    finally:
        cursor.close()

def _process_single_pdf_task(args):
    pdf_path, order_id, file_hash = args
    try:
        if not os.path.exists(pdf_path):
            return order_id, "Error - File not found", None, None, None, None, file_hash, None

        # Parse the PDF. This is the CPU-intensive part.
        boleta_id, purchase_date, purchase_time, products_data, totals = process_pdf(pdf_path)

        if not (boleta_id and products_data and purchase_date and totals):
            return order_id, "Error - Parsing failed", None, None, None, None, file_hash, None

        # Return all data to the parent process
        return order_id, "Processed", boleta_id, purchase_date, purchase_time, products_data, file_hash, totals

    except Exception as e:
        logging.error(f"Error en el subproceso para {os.path.basename(pdf_path)}: {e}", exc_info=True)
        return order_id, f"Error - Unexpected: {e}", None, None, None, None, file_hash, None

def main():
    """Función principal que orquesta el proceso de leer y procesar PDFs."""
    setup_logging()
    
    files_to_process = []
    # --- PASO 1: Obtener lista de archivos a procesar ---
    logging.info("Obteniendo lista de archivos a procesar desde la base de datos...")
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT ruta_archivo, order_id, file_hash FROM historial_descargas WHERE estado = 'Descargado'"
            cursor.execute(query)
            files_to_process = cursor.fetchall()
        logging.info(f"Se encontraron {len(files_to_process)} boletas para procesar.")
    except Exception as e:
        logging.error(f"No se pudo obtener la lista de archivos de la BD: {e}")
        return

    if not files_to_process:
        logging.info("No hay boletas nuevas para procesar.")
        return

    # --- PASO 2: Procesar PDFs en paralelo ---
    logging.info("Iniciando procesamiento en paralelo de archivos PDF...")
    with multiprocessing.Pool() as pool:
        results = pool.map(_process_single_pdf_task, files_to_process)
    logging.info("Procesamiento en paralelo completado.")

    # --- PASO 3: Insertar resultados en la BD secuencialmente ---
    logging.info("Insertando resultados en la base de datos...")
    try:
        with db_connection() as conn:
            source_id = get_source_id(conn, 'Jumbo')
            cursor = conn.cursor()
            
            # Create a map for original file paths
            file_path_map = {order_id: file_path for file_path, order_id, _ in files_to_process}

            for result in results:
                if not result:
                    continue
                
                order_id, status, boleta_id, purchase_date, purchase_time, products_data, file_hash, totals = result
                
                original_filepath = file_path_map.get(order_id)
                pdf_file = os.path.basename(original_filepath) if original_filepath else f"ID: {order_id}"

                if status == "Processed":
                    try:
                        # Start transaction for this file
                        conn.start_transaction()

                        # Insert metadata
                        metadata_id = insert_metadata(conn, source_id, original_filepath, file_hash, DOCUMENT_TYPE)
                        
                        # Insert staging data
                        insert_boleta_data_to_staging(
                            cursor, metadata_id, source_id, boleta_id, purchase_time, products_data
                        )
                        
                        # Validate staging data
                        if not validate_staging_data_jumbo(conn, metadata_id, len(products_data), totals):
                            logging.error(f"La validación de staging falló para {pdf_file}. Revirtiendo.")
                            ingestion_status_logger.info(f"FILE: {pdf_file} | HASH: {file_hash} | STATUS: Failed - Staging validation failed")
                            conn.rollback()
                            continue

                        # Update status in historial_descargas
                        cursor.execute("UPDATE historial_descargas SET estado = 'Procesado' WHERE order_id = %s", (order_id,))
                        
                        # If all good, commit the transaction for this file
                        conn.commit()
                        logging.info(f"Boleta {pdf_file} procesada y guardada exitosamente.")

                        # Move the file only after successful commit
                        processed_dir = os.path.join(os.path.dirname(original_filepath), 'procesados')
                        os.makedirs(processed_dir, exist_ok=True)
                        new_filename = generate_standardized_filename(
                            document_type=DOCUMENT_TYPE, document_period=purchase_date,
                            file_hash=file_hash, original_filename=pdf_file
                        )
                        processed_filepath = os.path.join(processed_dir, new_filename)
                        shutil.move(original_filepath, processed_filepath)
                        log_file_movement(original_filepath, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")
                        ingestion_status_logger.info(f"FILE: {new_filename} | HASH: {file_hash} | STATUS: Processed Successfully")

                    except Exception as e:
                        logging.error(f"Error al guardar datos para {pdf_file} en la BD: {e}")
                        ingestion_status_logger.info(f"FILE: {pdf_file} | HASH: {file_hash} | STATUS: Failed - DB insertion error")
                        conn.rollback()

                else:
                    # Handle parsing errors from the child process
                    logging.warning(f"No se pudo procesar completamente {pdf_file}. Estado: {status}.")
                    log_file_movement(original_filepath, "N/A", "FAILED", f"Error al procesar: {status}")
                    ingestion_status_logger.info(f"FILE: {pdf_file} | HASH: {file_hash} | STATUS: Failed - {status}")
        
        logging.info("Proceso completado. Revisa tu base de datos MySQL.")

    except Exception as e:
        logging.error(f"Ocurrió un error inesperado en el proceso principal: {e}", exc_info=True)
        ingestion_status_logger.info(f"GLOBAL_ERROR: Unexpected error - {e}")


if __name__ == "__main__":
    main()
