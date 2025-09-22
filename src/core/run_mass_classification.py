# -*- coding: utf-8 -*-
"""
Script para Clasificación Masiva de Transacciones

Este script utiliza el TransactionCategorizer para procesar todas las transacciones
almacenadas en las tablas 'raw' y de staging, asigna una categoría a cada una y 
guarda los resultados en una tabla dedicada (`resultados_clasificacion`).

Esto permite un análisis y validación de las reglas de clasificación antes de 
mover los datos a la tabla de negocio final `transactions`.
"""

import sys
import os
import logging

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from db.database_utils import db_connection
from core.transaction_categorizer import TransactionCategorizer

# --- Configuración ---
# Define las tablas a procesar y sus columnas relevantes.
TABLES_TO_PROCESS = [
    {
        "name": "raw_transacciones_cta_corriente",
        "id_col": "raw_id",
        "desc_col": "descripcion_transaccion"
    },
    {
        "name": "raw_transacciones_tarjeta_credito_nacional",
        "id_col": "raw_id",
        "desc_col": "descripcion_transaccion"
    },
    {
        "name": "raw_transacciones_tarjeta_credito_internacional",
        "id_col": "raw_id",
        "desc_col": "descripcion_transaccion"
    },
    {
        "name": "raw_transacciones_linea_credito",
        "id_col": "raw_id",
        "desc_col": "descripcion"
    },
    {
        "name": "staging_boletas_jumbo",
        "id_col": "id",
        "desc_col": "descripcion_producto"
    }
]

def setup_results_table(cursor):
    """Crea la tabla de resultados si no existe y la trunca."""
    logging.info("Configurando la tabla 'resultados_clasificacion'...")
    
    create_table_sql = ("""
    CREATE TABLE IF NOT EXISTS resultados_clasificacion (
        resultado_id INT AUTO_INCREMENT PRIMARY KEY,
        tabla_origen VARCHAR(255) NOT NULL,
        id_origen INT NOT NULL,
        descripcion_original TEXT,
        subcategoria_id_propuesta INT,
        fecha_clasificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_origen (tabla_origen, id_origen)
    );
    """)
    cursor.execute(create_table_sql)
    
    # Limpiar la tabla para una nueva ejecución
    cursor.execute("TRUNCATE TABLE resultados_clasificacion;")
    logging.info("Tabla de resultados configurada y limpia.")

def run_classification():
    """
    Orquesta el proceso de clasificación masiva.
    """
    logging.info("Iniciando proceso de clasificación masiva...")
    
    # 1. Inicializar el categorizador (carga las reglas)
    categorizer = TransactionCategorizer()
    if not categorizer.rules:
        logging.error("No se cargaron reglas de clasificación. Abortando proceso.")
        return

    try:
        with db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # 2. Preparar la tabla de resultados
            setup_results_table(cursor)

            # 3. Procesar cada tabla
            for table_info in TABLES_TO_PROCESS:
                table_name = table_info["name"]
                id_col = table_info["id_col"]
                desc_col = table_info["desc_col"]
                
                logging.info(f"Procesando tabla: {table_name}...")
                
                # Leer todas las transacciones de la tabla actual
                cursor.execute(f"SELECT {id_col}, {desc_col} FROM {table_name}")
                transactions = cursor.fetchall()

                if not transactions:
                    logging.info(f"No se encontraron transacciones en {table_name}. Saltando.")
                    continue

                # 4. Categorizar en memoria
                results_to_insert = []
                for trans in transactions:
                    description = trans[desc_col]
                    raw_id = trans[id_col]
                    
                    # Obtener la categoría propuesta
                    subcategory_id = categorizer.categorize(description)
                    
                    results_to_insert.append((
                        table_name,
                        raw_id,
                        description,
                        subcategory_id
                    ))
                
                # 5. Insertar los resultados en lote (batch)
                if results_to_insert:
                    sql_insert = ("""
                        INSERT INTO resultados_clasificacion 
                        (tabla_origen, id_origen, descripcion_original, subcategoria_id_propuesta)
                        VALUES (%s, %s, %s, %s)
                    """)
                    cursor.executemany(sql_insert, results_to_insert)
                    conn.commit()
                    logging.info(f"Insertados {cursor.rowcount} resultados para la tabla {table_name}.")

    except Exception as e:
        logging.error(f"Ha ocurrido un error durante la clasificación masiva: {e}")

    logging.info("Proceso de clasificación masiva completado.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_classification()