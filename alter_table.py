
import logging
from database_utils import db_connection

def reset_and_setup_bank_tables():
    """
    Resetea las tablas bancarias y aplica la estructura final con file_hash.
    ADVERTENCIA: Esta operación es destructiva y borrará todos los datos existentes
    en las tablas 'bank_account_transactions_raw' y 'bank_statement_metadata_raw'.
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            logging.warning("Iniciando reseteo de tablas bancarias...")
            
            # 1. Desactivar temporalmente la revisión de llaves foráneas
            logging.info("Desactivando revisión de llaves foráneas.")
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            
            # 2. Vaciar las tablas principales
            logging.info("Vaciando tabla 'bank_account_transactions_raw'...")
            cursor.execute("TRUNCATE TABLE bank_account_transactions_raw")
            logging.info("Vaciando tabla 'bank_statement_metadata_raw'...")
            cursor.execute("TRUNCATE TABLE bank_statement_metadata_raw")
            
            # 3. Eliminar y recrear credit_card_transactions_raw para asegurar el esquema
            logging.info("Eliminando tabla 'credit_card_transactions_raw' si existe...")
            cursor.execute("DROP TABLE IF EXISTS `credit_card_transactions_raw`")

            logging.info("Creando tabla 'credit_card_transactions_raw' con el esquema actualizado...")
            create_credit_card_table_query = """
            CREATE TABLE `credit_card_transactions_raw` (
              `raw_id` int NOT NULL AUTO_INCREMENT,
              `source_id` int NOT NULL,
              `metadata_id` int NOT NULL,
              `original_charge_date` DATE DEFAULT NULL,
              `installment_charge_date` DATE DEFAULT NULL,
              `transaction_description` text COLLATE utf8mb4_unicode_ci,
              `category` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              `current_installment` int DEFAULT NULL,
              `total_installments` int DEFAULT NULL,
              `charges_pesos` decimal(15,2) DEFAULT NULL,
              `amount_usd` decimal(15,2) DEFAULT NULL, -- Nueva columna para monto en USD
              `exchange_rate` decimal(15,4) DEFAULT NULL, -- Nueva columna para tipo de cambio
              `country` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL, -- Nueva columna para país
              `credits_pesos` decimal(15,2) DEFAULT NULL,
              `original_line_data` text COLLATE utf8mb4_unicode_ci,
              `processed_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`raw_id`),
              KEY `source_id` (`source_id`),
              KEY `metadata_id` (`metadata_id`),
              CONSTRAINT `credit_card_transactions_raw_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `sources` (`source_id`),
              CONSTRAINT `credit_card_transactions_raw_ibfk_2` FOREIGN KEY (`metadata_id`) REFERENCES `bank_statement_metadata_raw` (`metadata_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_credit_card_table_query)
            logging.info("Tabla 'credit_card_transactions_raw' creada/asegurada con el esquema actualizado.")

            # 4. Reactivar la revisión de llaves foráneas
            logging.info("Reactivando revisión de llaves foráneas.")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

            # 5. Asegurar columnas necesarias en bank_statement_metadata_raw (si no existen)
            cursor.execute("SHOW COLUMNS FROM bank_statement_metadata_raw LIKE 'file_hash'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE bank_statement_metadata_raw ADD COLUMN file_hash VARCHAR(64) NOT NULL UNIQUE AFTER original_filename")
                logging.info("Columna 'file_hash' agregada a bank_statement_metadata_raw.")
            
            cursor.execute("SHOW COLUMNS FROM bank_statement_metadata_raw LIKE 'document_type'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE bank_statement_metadata_raw ADD COLUMN document_type VARCHAR(255) AFTER file_hash")
                logging.info("Columna 'document_type' agregada a bank_statement_metadata_raw.")

            conn.commit()
            logging.info("Las tablas bancarias han sido reseteadas y configuradas exitosamente.")

    except Exception as e:
        logging.error(f"Ocurrió un error durante el reseteo y configuración: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    reset_and_setup_bank_tables()
