# -*- coding: utf-8 -*-
"""Script orquestador para procesar los archivos PDF de boletas."""

import logging
import os
import mysql.connector
import multiprocessing

# Importar módulos y configuración del proyecto
from config import PROCESS_LOG_FILE
from database_utils import db_connection
from pdf_parser import process_pdf


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


def create_table_if_not_exists(cursor):
    """Verifica y, si es necesario, crea la tabla 'boletas_data'."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS boletas_data (
        boleta_id VARCHAR(255),
        filename VARCHAR(255),
        Fecha DATE,
        Hora TIME,  # Nueva columna para la hora
        codigo_SKU VARCHAR(255),
        Cantidad_unidades INT,
        Valor_Unitario DECIMAL(15, 2),
        Cantidad_comprada_X_Valor_Unitario VARCHAR(255),
        Descripcion_producto TEXT,
        Total_a_pagar_producto DECIMAL(15, 2),
        Descripcion_Oferta TEXT,
        Cantidad_reducida_del_total DECIMAL(15, 2),
        Categoria VARCHAR(255),
        PRIMARY KEY (boleta_id, codigo_SKU) # Clave primaria compuesta
    )
    """
    cursor.execute(create_table_query)
    logging.info("Tabla 'boletas_data' verificada/creada exitosamente.")


def get_files_to_process(cursor):
    """Obtiene de la BD la lista de archivos que necesitan ser procesados."""
    query = (
        "SELECT file_path, order_id FROM download_history WHERE status = 'Downloaded'"
    )
    cursor.execute(query)
    return cursor.fetchall()


def update_status(cursor, order_id, status):
    """Actualiza el estado de un registro en la tabla de historial."""
    query = "UPDATE download_history SET status = %s WHERE order_id = %s"
    cursor.execute(query, (status, order_id))


def insert_boleta_data(cursor, boleta_id, filename, purchase_time, products_data):
    """Inserta una lista de productos de una boleta en la base de datos."""
    insert_query = """
    INSERT INTO boletas_data (
        boleta_id, filename, Fecha, Hora, codigo_SKU, Cantidad_unidades,
        Valor_Unitario, Cantidad_comprada_X_Valor_Unitario,
        Descripcion_producto, Total_a_pagar_producto,
        Descripcion_Oferta, Cantidad_reducida_del_total, Categoria
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        Cantidad_unidades=VALUES(Cantidad_unidades),
        Valor_Unitario=VALUES(Valor_Unitario),
        Cantidad_comprada_X_Valor_Unitario=VALUES(Cantidad_comprada_X_Valor_Unitario),
        Descripcion_producto=VALUES(Descripcion_producto),
        Total_a_pagar_producto=VALUES(Total_a_pagar_producto),
        Descripcion_Oferta=VALUES(Descripcion_Oferta),
        Cantidad_reducida_del_total=VALUES(Cantidad_reducida_del_total),
        Categoria=VALUES(Categoria);
    """
    for product in products_data:
        try:
            data_tuple = (
                boleta_id,
                filename,
                product["Fecha"],
                purchase_time,  # Usar la hora extraída del PDF
                product["codigo_SKU"],
                product["Cantidad_unidades"],
                product["Valor_Unitario"],
                product["Cantidad_comprada_X_Valor_Unitario"],
                product["Descripcion_producto"],
                product["Total_a_pagar_producto"],
                product["Descripcion_Oferta"],
                product["Cantidad_reducida_del_total"],
                product["Categoria"],
            )
            cursor.execute(insert_query, data_tuple)
        except mysql.connector.Error as err:
            sku = product.get('codigo_SKU', 'N/A')
            logging.error(
                f"Error al insertar SKU {sku} de {filename}: {err}"
            )


def _process_single_pdf_task(args):
    pdf_path, order_id = args
    try:
        if not os.path.exists(pdf_path):
            return order_id, "Error - File not found", None, None, None

        boleta_id, purchase_date, purchase_time, products_data = process_pdf(pdf_path)

        if boleta_id and products_data:
            return order_id, "Processed", boleta_id, purchase_time, products_data
        else:
            return order_id, "Error - Parsing failed", None, None, None
    except Exception as e:
        return order_id, f"Error - Unexpected: {e}", None, None, None


def main():
    """Función principal que orquesta el proceso de leer y procesar PDFs."""
    setup_logging()
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            create_table_if_not_exists(cursor)
            conn.commit()

            files_to_process = get_files_to_process(cursor)
            file_path_map = {order_id: file_path for file_path, order_id in files_to_process}

            # Use multiprocessing Pool to process PDFs in parallel
            with multiprocessing.Pool() as pool:
                results = pool.imap_unordered(_process_single_pdf_task, files_to_process)

                for order_id, status, boleta_id, purchase_time, products_data in results:
                    # Get original filename for logging
                    pdf_file = os.path.basename(file_path_map[order_id])

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
                    else:
                        update_status(cursor, order_id, status)
                        conn.commit()
                        msg = (f"No se pudo procesar completamente {pdf_file}. "
                               f"Estado: {status}. Saltando.")
                        logging.warning(msg)

        logging.info("Proceso completado. Revisa tu base de datos MySQL.")

    except mysql.connector.Error:
        logging.error("El script terminó debido a un error con la base de datos.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado en el proceso principal: {e}")


if __name__ == "__main__":
    main()
