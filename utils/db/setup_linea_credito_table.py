import logging
from database_utils import db_connection

def setup_linea_credito_table():
    """
    Crea la tabla 'raw_transacciones_linea_credito' si no existe.
    Esta tabla almacenará los datos crudos de las cartolas de línea de crédito,
    siguiendo la arquitectura de una tabla por tipo de producto.
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            logging.info("Verificando/Creando la tabla 'raw_transacciones_linea_credito'...")
            
            create_table_query = """
            CREATE TABLE IF NOT EXISTS `raw_transacciones_linea_credito` (
              `raw_id` INT NOT NULL AUTO_INCREMENT,
              `fuente_id` INT NOT NULL,
              `metadata_id` INT NOT NULL,
              `fecha_transaccion` DATE DEFAULT NULL,
              `descripcion` TEXT,
              `cargos` DECIMAL(15,2) DEFAULT NULL,
              `abonos` DECIMAL(15,2) DEFAULT NULL,
              `monto_utilizado` DECIMAL(15,2) DEFAULT NULL,
              `tasa_diaria` DECIMAL(15,4) DEFAULT NULL,
              `intereses` DECIMAL(15,2) DEFAULT NULL,
              `linea_original_datos` TEXT,
              `procesado_en` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`raw_id`),
              KEY `fuente_id` (`fuente_id`),
              KEY `metadata_id` (`metadata_id`),
              CONSTRAINT `fk_linea_credito_fuente` FOREIGN KEY (`fuente_id`) REFERENCES `fuentes` (`fuente_id`),
              CONSTRAINT `fk_linea_credito_metadata` FOREIGN KEY (`metadata_id`) REFERENCES `raw_metadatos_cartolas_bancarias` (`metadata_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            cursor.execute(create_table_query)
            conn.commit()
            
            logging.info("La tabla 'raw_transacciones_linea_credito' está lista.")

    except Exception as e:
        logging.error(f"Ocurrió un error durante la configuración de la tabla: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    setup_linea_credito_table()