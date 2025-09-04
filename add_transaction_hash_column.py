import logging
from database_utils import db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_transaction_hash_column():
    """
    Añade la columna `transaction_hash` a `transacciones_tarjeta_credito_raw`
    y la hace UNIQUE.
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            logging.info("Verificando si la columna 'transaction_hash' existe en transacciones_tarjeta_credito_raw...")
            cursor.execute("SHOW COLUMNS FROM transacciones_tarjeta_credito_raw LIKE 'transaction_hash'")
            if not cursor.fetchone():
                logging.info("Añadiendo columna 'transaction_hash' a transacciones_tarjeta_credito_raw...")
                cursor.execute("ALTER TABLE transacciones_tarjeta_credito_raw ADD COLUMN transaction_hash VARCHAR(64) NOT NULL UNIQUE AFTER abonos_pesos")
                logging.info("Columna 'transaction_hash' añadida con éxito y configurada como UNIQUE.")
            else:
                logging.info("La columna 'transaction_hash' ya existe.")
            
            conn.commit()
            cursor.close()
            logging.info("Proceso de actualización de esquema completado.")

    except Exception as e:
        logging.error(f"Ocurrió un error al añadir la columna transaction_hash: {e}")

if __name__ == '__main__':
    add_transaction_hash_column()
