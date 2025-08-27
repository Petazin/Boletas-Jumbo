
import logging
from database_utils import db_connection

def reset_and_setup_bank_tables():
    """
    Resetea las tablas bancarias y aplica la estructura final con file_hash.
    ADVERTENCIA: Esta operación es destructiva y borrará todos los datos existentes
    en las tablas 'transacciones_cuenta_bancaria_raw' y 'metadatos_cartolas_bancarias_raw'.
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            logging.warning("Iniciando reseteo de tablas bancarias...")
            
            # 1. Desactivar temporalmente la revisión de llaves foráneas
            logging.info("Desactivando revisión de llaves foráneas.")
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            
            # 2. Vaciar las tablas principales
            logging.info("Vaciando tabla 'transacciones_cuenta_bancaria_raw'...")
            cursor.execute("TRUNCATE TABLE transacciones_cuenta_bancaria_raw")
            logging.info("Vaciando tabla 'metadatos_cartolas_bancarias_raw'...")
            cursor.execute("TRUNCATE TABLE metadatos_cartolas_bancarias_raw")
            
            # 3. Eliminar y recrear transacciones_tarjeta_credito_raw para asegurar el esquema
            logging.info("Eliminando tabla 'transacciones_tarjeta_credito_raw' si existe...")
            cursor.execute("DROP TABLE IF EXISTS `transacciones_tarjeta_credito_raw`")

            logging.info("Creando tabla 'transacciones_tarjeta_credito_raw' con el esquema actualizado...")
            create_credit_card_table_query = """
            CREATE TABLE `transacciones_tarjeta_credito_raw` (
              `raw_id` int NOT NULL AUTO_INCREMENT,
              `fuente_id` int NOT NULL,
              `metadata_id` int NOT NULL,
              `fecha_cargo_original` DATE DEFAULT NULL,
              `fecha_cargo_cuota` DATE DEFAULT NULL,
              `descripcion_transaccion` text COLLATE utf8mb4_unicode_ci,
              `categoria` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              `cuota_actual` int DEFAULT NULL,
              `total_cuotas` int DEFAULT NULL,
              `cargos_pesos` decimal(15,2) DEFAULT NULL,
              `monto_usd` decimal(15,2) DEFAULT NULL,
              `tipo_cambio` decimal(15,4) DEFAULT NULL,
              `pais` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              `abonos_pesos` decimal(15,2) DEFAULT NULL,
              `linea_original_datos` text COLLATE utf8mb4_unicode_ci,
              `procesado_en` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`raw_id`),
              KEY `fuente_id` (`fuente_id`),
              KEY `metadata_id` (`metadata_id`),
              CONSTRAINT `transacciones_tarjeta_credito_raw_ibfk_1` FOREIGN KEY (`fuente_id`) REFERENCES `fuentes` (`fuente_id`),
              CONSTRAINT `transacciones_tarjeta_credito_raw_ibfk_2` FOREIGN KEY (`metadata_id`) REFERENCES `metadatos_cartolas_bancarias_raw` (`metadata_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_credit_card_table_query)
            logging.info("Tabla 'transacciones_tarjeta_credito_raw' creada/asegurada con el esquema actualizado.")

            # 4. Reactivar la revisión de llaves foráneas
            logging.info("Reactivando revisión de llaves foráneas.")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

            # 5. Asegurar columnas necesarias en metadatos_cartolas_bancarias_raw (si no existen)
            cursor.execute("SHOW COLUMNS FROM metadatos_cartolas_bancarias_raw LIKE 'file_hash'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE metadatos_cartolas_bancarias_raw ADD COLUMN file_hash VARCHAR(64) NOT NULL UNIQUE AFTER nombre_archivo_original")
                logging.info("Columna 'file_hash' agregada a metadatos_cartolas_bancarias_raw.")
            
            cursor.execute("SHOW COLUMNS FROM metadatos_cartolas_bancarias_raw LIKE 'document_type'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE metadatos_cartolas_bancarias_raw ADD COLUMN document_type VARCHAR(255) AFTER file_hash")
                logging.info("Columna 'document_type' agregada a metadatos_cartolas_bancarias_raw.")

            conn.commit()
            logging.info("Las tablas bancarias han sido reseteadas y configuradas exitosamente.")

    except Exception as e:
        logging.error(f"Ocurrió un error durante el reseteo y configuración: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    reset_and_setup_bank_tables()
