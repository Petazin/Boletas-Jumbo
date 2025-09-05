import logging
from database_utils import db_connection

def reset_and_setup_bank_tables():
    """
    Resetea las tablas bancarias y aplica la estructura final con file_hash.
    ADVERTENCIA: Esta operación es destructiva y borrará todos los datos existentes
    en las tablas bancarias raw.
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            logging.warning("Iniciando reseteo de tablas bancarias...")
            
            # 1. Desactivar temporalmente la revisión de llaves foráneas
            logging.info("Desactivando revisión de llaves foráneas.")
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            
            # 2. Vaciar las tablas principales
            logging.info("Vaciando tabla 'raw_transacciones_cta_corriente'...")
            cursor.execute("TRUNCATE TABLE raw_transacciones_cta_corriente")
            logging.info("Vaciando tabla 'raw_metadatos_cartolas_bancarias'...")
            cursor.execute("TRUNCATE TABLE raw_metadatos_cartolas_bancarias")
            
            # 3. Eliminar y recrear las tablas de tarjeta de crédito para asegurar el nuevo esquema
            logging.info("Eliminando tablas de tarjeta de crédito si existen...")
            cursor.execute("DROP TABLE IF EXISTS `raw_transacciones_tarjeta_credito_nacional`")
            cursor.execute("DROP TABLE IF EXISTS `raw_transacciones_tarjeta_credito_internacional`")
            cursor.execute("DROP TABLE IF EXISTS `raw_transacciones_tarjeta_credito`") # Eliminar la tabla antigua por si acaso

            logging.info("Creando tabla 'raw_transacciones_tarjeta_credito_nacional'...")
            create_tc_nacional_query = """
            CREATE TABLE `raw_transacciones_tarjeta_credito_nacional` (
                `raw_id` int NOT NULL AUTO_INCREMENT,
                `fuente_id` int NOT NULL,
                `metadata_id` int NOT NULL,
                `fecha_cargo_original` date DEFAULT NULL,
                `fecha_cargo_cuota` date DEFAULT NULL,
                `descripcion_transaccion` text,
                `cuota_actual` int DEFAULT NULL,
                `total_cuotas` int DEFAULT NULL,
                `cargos_pesos` decimal(15,2) DEFAULT NULL,
                `abonos_pesos` decimal(15,2) DEFAULT NULL,
                `linea_original_datos` text,
                `procesado_en` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`raw_id`),
                KEY `fuente_id` (`fuente_id`),
                KEY `metadata_id` (`metadata_id`),
                FOREIGN KEY (`fuente_id`) REFERENCES `fuentes` (`fuente_id`),
                FOREIGN KEY (`metadata_id`) REFERENCES `raw_metadatos_cartolas_bancarias` (`metadata_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
            cursor.execute(create_tc_nacional_query)

            logging.info("Creando tabla 'raw_transacciones_tarjeta_credito_internacional'...")
            create_tc_internacional_query = """
            CREATE TABLE `raw_transacciones_tarjeta_credito_internacional` (
                `raw_id` int NOT NULL AUTO_INCREMENT,
                `fuente_id` int NOT NULL,
                `metadata_id` int NOT NULL,
                `fecha_cargo_original` date DEFAULT NULL,
                `fecha_cargo_cuota` date DEFAULT NULL,
                `descripcion_transaccion` text,
                `categoria` varchar(255) DEFAULT NULL,
                `cuota_actual` int DEFAULT NULL,
                `total_cuotas` int DEFAULT NULL,
                `cargos_pesos` decimal(15,2) DEFAULT NULL,
                `abonos_pesos` decimal(15,2) DEFAULT NULL,
                `monto_usd` decimal(15,2) DEFAULT NULL,
                `tipo_cambio` decimal(10,4) DEFAULT NULL,
                `pais` varchar(255) DEFAULT NULL,
                `procesado_en` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`raw_id`),
                KEY `fuente_id` (`fuente_id`),
                KEY `metadata_id` (`metadata_id`),
                FOREIGN KEY (`fuente_id`) REFERENCES `fuentes` (`fuente_id`),
                FOREIGN KEY (`metadata_id`) REFERENCES `raw_metadatos_cartolas_bancarias` (`metadata_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
            cursor.execute(create_tc_internacional_query)
            logging.info("Tablas de tarjeta de crédito creadas con el nuevo esquema.")

            # 4. Reactivar la revisión de llaves foráneas
            logging.info("Reactivando revisión de llaves foráneas.")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

            # 5. Asegurar columnas necesarias en raw_metadatos_cartolas_bancarias (si no existen)
            cursor.execute("SHOW COLUMNS FROM raw_metadatos_cartolas_bancarias LIKE 'file_hash'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE raw_metadatos_cartolas_bancarias ADD COLUMN file_hash VARCHAR(64) NOT NULL UNIQUE AFTER nombre_archivo_original")
                logging.info("Columna 'file_hash' agregada a raw_metadatos_cartolas_bancarias.")
            
            cursor.execute("SHOW COLUMNS FROM raw_metadatos_cartolas_bancarias LIKE 'document_type'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE raw_metadatos_cartolas_bancarias ADD COLUMN document_type VARCHAR(255) AFTER file_hash")
                logging.info("Columna 'document_type' agregada a raw_metadatos_cartolas_bancarias.")

            conn.commit()
            logging.info("Las tablas bancarias han sido reseteadas y configuradas exitosamente.")

    except Exception as e:
        logging.error(f"Ocurrió un error durante el reseteo y configuración: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    reset_and_setup_bank_tables()