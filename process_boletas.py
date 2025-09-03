# -*- coding: utf-8 -*-
"""Script orquestador para procesar los archivos PDF de boletas."""

import logging
import os
import mysql.connector
import multiprocessing
import shutil

# Importar módulos y configuración del proyecto
from config import PROCESS_LOG_FILE
from database_utils import db_connection
from pdf_parser import process_pdf
from utils.file_utils import log_file_movement


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





def get_files_to_process(cursor):
    """Obtiene de la BD la lista de archivos que necesitan ser procesados."""
    query = (
        "SELECT ruta_archivo, order_id, file_hash FROM historial_descargas WHERE estado = 'Descargado'"
    )
    cursor.execute(query)
    return cursor.fetchall()


def update_status(cursor, order_id, status):
    """Actualiza el estado de un registro en la tabla de historial."""
    query = "UPDATE historial_descargas SET estado = %s WHERE order_id = %s"
    cursor.execute(query, (status, order_id))


def insert_boleta_data(cursor, boleta_id, filename, purchase_time, products_data):
    """Inserta una lista de productos de una boleta en la base de datos."""
    insert_query = """
    INSERT INTO transacciones_jumbo (
        transaccion_id, nombre_archivo, fecha_compra, hora_compra, sku, cantidad,
        precio_unitario, cantidad_X_precio_unitario,
        descripcion_producto, precio_total_item,
        descripcion_oferta, monto_descuento, categoria
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        cantidad=VALUES(cantidad),
        precio_unitario=VALUES(precio_unitario),
        cantidad_X_precio_unitario=VALUES(cantidad_X_precio_unitario),
        descripcion_producto=VALUES(descripcion_producto),
        precio_total_item=VALUES(precio_total_item),
        descripcion_oferta=VALUES(descripcion_oferta),
        monto_descuento=VALUES(monto_descuento),
        categoria=VALUES(categoria);
    """
    for product in products_data:
        try:
            data_tuple = (
                boleta_id,
                filename,
                product["fecha_transaccion"],
                purchase_time,  # Usar la hora extraída del PDF
                product["sku"],
                product["cantidad"],
                product["precio_unitario"],
                product["Cantidad_comprada_X_Valor_Unitario"],
                product["descripcion_producto"],
                product["precio_total_item"],
                product["descripcion_oferta"],
                product["monto_descuento"],
                product["categoria"],
            )
            cursor.execute(insert_query, data_tuple)
        except mysql.connector.Error as err:
            sku = product.get('sku', 'N/A')
            logging.error(
                f"Error al insertar SKU {sku} de {filename}: {err}"
            )


def _process_single_pdf_task(args):
    pdf_path, order_id, file_hash = args
    try:
        if not os.path.exists(pdf_path):
            return order_id, "Error - File not found", None, None, None, None

        boleta_id, purchase_date, purchase_time, products_data = process_pdf(pdf_path)

        if boleta_id and products_data:
            return order_id, "Processed", boleta_id, purchase_time, products_data, file_hash
        else:
            return order_id, "Error - Parsing failed", None, None, None, None
    except Exception as e:
        return order_id, f"Error - Unexpected: {e}", None, None, None, None


def main():
    """Función principal que orquesta el proceso de leer y procesar PDFs."""
    setup_logging()
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            conn.commit()

            files_to_process = get_files_to_process(cursor)
            file_path_map = {order_id: (file_path, file_hash) for file_path, order_id, file_hash in files_to_process}

            # Use multiprocessing Pool to process PDFs in parallel
            with multiprocessing.Pool() as pool:
                results = pool.imap_unordered(_process_single_pdf_task, files_to_process)

                for order_id, status, boleta_id, purchase_time, products_data, file_hash in results:
                    # Get original filename for logging
                    pdf_file = os.path.basename(file_path_map[order_id][0])

                    if status == "Processed":
                        insert_boleta_data(
                            cursor,
                            boleta_id,
                            pdf_file,
                            purchase_time,
                            products_data
                        )
                        update_status(cursor, order_id, "Processed")
                        conn.commit()
                        msg = f"Datos de {pdf_file} insertados correctamente."
                        logging.info(msg)
                        ingestion_status_logger.info(f"FILE: {pdf_file} | HASH: {file_hash} | STATUS: Processed Successfully")

                        # Mover el archivo PDF a la carpeta de procesados
                        original_filepath = file_path_map[order_id][0]
                        processed_dir = os.path.join(os.path.dirname(original_filepath), 'procesados')
                        os.makedirs(processed_dir, exist_ok=True)
                        processed_filepath = os.path.join(processed_dir, os.path.basename(original_filepath))
                        shutil.move(original_filepath, processed_filepath)
                        log_file_movement(original_filepath, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")

                    else:
                        update_status(cursor, order_id, status)
                        conn.commit()
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