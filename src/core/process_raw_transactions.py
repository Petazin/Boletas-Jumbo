# -*- coding: utf-8 -*-
"""
Módulo para procesar las transacciones desde las tablas raw,
enriquecerlas (ej. con categorías) y moverlas a la tabla final 'transactions'.
"""

import logging
import sys
import os
import hashlib

# Añadir el directorio 'src' al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database_utils import db_connection
from core.transaction_categorizer import get_transaction_category

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_transaction_id(raw_transaction_dict):
    """
    Genera un ID único para una transacción basado en su contenido.
    """
    # Concatenar valores clave de la transacción para crear un string único
    unique_string = (
        f"{raw_transaction_dict.get('raw_id', '')}-"
        f"{raw_transaction_dict.get('fuente_id', '')}-"
        f"{raw_transaction_dict.get('metadata_id', '')}-"
        f"{raw_transaction_dict.get('descripcion_transaccion', '')}-"
        f"{raw_transaction_dict.get('fecha_transaccion_str', '')}-"
        f"{raw_transaction_dict.get('cargos_pesos', '')}-"
        f"{raw_transaction_dict.get('abonos_pesos', '')}"
    )
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

def process_raw_cta_corriente():
    """
    Procesa las transacciones de 'raw_transacciones_cta_corriente' y las
    mueve a la tabla 'transactions'.
    """
    logging.info("Iniciando procesamiento de 'raw_transacciones_cta_corriente'.")
    
    try:
        with db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Seleccionar transacciones que aún no han sido procesadas
            # Se busca el raw_id en la tabla 'transactions' para evitar duplicados.
            query = """
            SELECT raw.* 
            FROM raw_transacciones_cta_corriente raw
            LEFT JOIN transactions t ON raw.raw_id = t.raw_id_original 
                                   AND t.fuente_id = raw.fuente_id
            WHERE t.transaccion_id IS NULL
            """
            cursor.execute(query)
            raw_transactions = cursor.fetchall()
            
            logging.info(f"Se encontraron {len(raw_transactions)} transacciones de cta. corriente para procesar.")
            
            processed_count = 0
            for raw_tx in raw_transactions:
                description = raw_tx['descripcion_transaccion']
                
                # 1. Obtener categoría usando el nuevo módulo
                subcategory_id = get_transaction_category(description)
                
                # 2. Determinar monto y tipo de transacción
                monto = 0
                tipo_transaccion = None
                if raw_tx.get('cargos_pesos') and raw_tx['cargos_pesos'] > 0:
                    monto = raw_tx['cargos_pesos']
                    tipo_transaccion = 'Gasto'
                elif raw_tx.get('abonos_pesos') and raw_tx['abonos_pesos'] > 0:
                    monto = raw_tx['abonos_pesos']
                    tipo_transaccion = 'Ingreso'
                else:
                    continue # Omitir si no hay monto o es cero

                # 3. Generar ID único para la transacción final
                transaction_id = generate_transaction_id(raw_tx)

                # 4. Preparar e insertar en la tabla 'transactions'
                insert_query = """
                INSERT INTO transactions (
                    transaccion_id, fuente_id, raw_id_original, metadata_id_original,
                    fecha_transaccion, descripcion, monto, tipo_transaccion, subcategoria_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                insert_values = (
                    transaction_id,
                    raw_tx['fuente_id'],
                    raw_tx['raw_id'],
                    raw_tx['metadata_id'],
                    raw_tx['fecha_transaccion_str'],
                    description,
                    monto,
                    tipo_transaccion,
                    subcategory_id
                )
                
                cursor.execute(insert_query, insert_values)
                processed_count += 1

            conn.commit()
            logging.info(f"Se procesaron e insertaron {processed_count} nuevas transacciones de cta. corriente.")

    except Exception as e:
        logging.error(f"Error al procesar transacciones de cuenta corriente: {e}", exc_info=True)

def main():
    """Función principal para orquestar el procesamiento de todas las tablas raw."""
    logging.info("--- INICIO DEL PROCESO DE TRANSFORMACIÓN RAW -> FINAL ---")
    
    # Por ahora, solo procesamos cta. corriente. Luego se añadirán las demás.
    process_raw_cta_corriente()
    
    logging.info("--- FIN DEL PROCESO DE TRANSFORMACIÓN ---")

if __name__ == '__main__':
    main()
