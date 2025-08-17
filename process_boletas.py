# -*- coding: utf-8 -*-
"""Script orquestador para procesar los archivos PDF de boletas."""

import logging
import os
import mysql.connector

# Importar módulos y configuración del proyecto
from config import BOLETAS_DIR, PROCESS_LOG_FILE
from database_utils import db_connection
from pdf_parser import process_pdf

def setup_logging():
    """Configura el sistema de logging para este script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(PROCESS_LOG_FILE, mode='w'),
            logging.StreamHandler()
        ]
    )

def create_table_if_not_exists(cursor):
    """Verifica y, si es necesario, crea la tabla 'boletas_data' en la base de datos."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS boletas_data (
        boleta_id VARCHAR(255),
        filename VARCHAR(255), 
        Fecha DATE,
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

def file_was_processed(cursor, filename):
    """Verifica en la base de datos si un archivo PDF ya ha sido procesado."""
    check_query = "SELECT 1 FROM boletas_data WHERE filename = %s LIMIT 1"
    cursor.execute(check_query, (filename,))
    return cursor.fetchone() is not None

def insert_boleta_data(cursor, boleta_id, filename, products_data):
    """Inserta una lista de productos de una boleta en la base de datos."""
    insert_query = """
    INSERT INTO boletas_data (
        boleta_id, filename, Fecha, codigo_SKU, Cantidad_unidades, Valor_Unitario, Cantidad_comprada_X_Valor_Unitario,
        Descripcion_producto, Total_a_pagar_producto,
        Descripcion_Oferta, Cantidad_reducida_del_total, Categoria
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        Cantidad_unidades=VALUES(Cantidad_unidades), Valor_Unitario=VALUES(Valor_Unitario),
        Cantidad_comprada_X_Valor_Unitario=VALUES(Cantidad_comprada_X_Valor_Unitario),
        Descripcion_producto=VALUES(Descripcion_producto), Total_a_pagar_producto=VALUES(Total_a_pagar_producto),
        Descripcion_Oferta=VALUES(Descripcion_Oferta), Cantidad_reducida_del_total=VALUES(Cantidad_reducida_del_total),
        Categoria=VALUES(Categoria);
    """
    for product in products_data:
        try:
            data_tuple = (
                boleta_id,
                filename,
                product['Fecha'],
                product['codigo_SKU'],
                product['Cantidad_unidades'],
                product['Valor_Unitario'],
                product['Cantidad_comprada_X_Valor_Unitario'],
                product['Descripcion_producto'],
                product['Total_a_pagar_producto'],
                product['Descripcion_Oferta'],
                product['Cantidad_reducida_del_total'],
                product['Categoria']
            )
            cursor.execute(insert_query, data_tuple)
        except mysql.connector.Error as err:
            logging.error(f"Error al insertar SKU {product.get('codigo_SKU', 'N/A')} de {filename}: {err}")

def main():
    """Función principal que orquesta el proceso de leer PDFs, procesarlos y guardar los datos."""
    setup_logging()
    try:
        # Utiliza el manejador de contexto para una conexión segura a la BD
        with db_connection() as conn:
            cursor = conn.cursor()
            create_table_if_not_exists(cursor)
            conn.commit() # Guardar la creación de la tabla

            # Obtener la lista de archivos PDF en el directorio
            pdf_files = [f for f in os.listdir(BOLETAS_DIR) if f.endswith('.pdf')]
            
            for pdf_file in pdf_files:
                # Primero, verificar si el archivo ya fue procesado para evitar trabajo innecesario
                if file_was_processed(cursor, pdf_file):
                    logging.info(f"Archivo {pdf_file} ya procesado. Saltando.")
                    continue

                pdf_path = os.path.join(BOLETAS_DIR, pdf_file)
                # Llamar al módulo parser para obtener los datos del PDF
                boleta_id, _, products_data = process_pdf(pdf_path)

                if boleta_id and products_data:
                    # Si se obtuvieron datos, insertarlos en la base de datos
                    insert_boleta_data(cursor, boleta_id, pdf_file, products_data)
                    conn.commit() # Guardar los datos de la boleta actual
                    logging.info(f"Datos de {pdf_file} insertados correctamente.")
                else:
                    logging.warning(f"No se pudo procesar completamente {pdf_file}. Saltando.")

        logging.info("\nProceso completado. Revisa tu base de datos MySQL.")

    except mysql.connector.Error:
        # Este error ya es logueado por database_utils, aquí solo se añade contexto.
        logging.error("El script terminó debido a un error con la base de datos.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado en el proceso principal: {e}")

if __name__ == "__main__":
    main()
