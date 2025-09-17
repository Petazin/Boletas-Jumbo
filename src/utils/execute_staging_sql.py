import mysql.connector
import os
from database_utils import db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sql_content = """
-- Tabla de staging para metadatos de extractos bancarios de Banco de Chile (de bank_ingestion.py)
CREATE TABLE IF NOT EXISTS banco_chile_cuenta_corriente_metadata_staging (
    metadata_id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    account_holder_name VARCHAR(255),
    rut VARCHAR(50),
    account_number VARCHAR(100),
    currency VARCHAR(10),
    statement_issue_date DATE,
    statement_folio VARCHAR(100),
    accounting_balance DECIMAL(18, 2),
    retentions_24hrs DECIMAL(18, 2),
    retentions_48hrs DECIMAL(18, 2),
    initial_balance DECIMAL(18, 2),
    available_balance DECIMAL(18, 2),
    credit_line_amount DECIMAL(18, 2),
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bcc_meta_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para metadatos de documentos en general (todos los demás scripts)
CREATE TABLE IF NOT EXISTS document_metadata_staging (
    metadata_id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    document_type VARCHAR(100),
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_doc_meta_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para transacciones de extractos bancarios de Banco de Chile (de bank_ingestion.py)
CREATE TABLE IF NOT EXISTS banco_chile_cuenta_corriente_transactions_staging (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    source_id INT NOT NULL,
    transaction_date_str VARCHAR(50),
    transaction_description VARCHAR(255),
    channel_or_branch VARCHAR(255),
    charges_pesos VARCHAR(50),
    credits_pesos VARCHAR(50),
    balance_pesos VARCHAR(50),
    original_line_data TEXT,
    file_hash VARCHAR(64) NOT NULL,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bcct_meta FOREIGN KEY (metadata_id) REFERENCES banco_chile_cuenta_corriente_metadata_staging(metadata_id),
    CONSTRAINT fk_bcct_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para transacciones de tarjetas de crédito nacionales (de ingest_xls_national_cc.py)
CREATE TABLE IF NOT EXISTS banco_chile_tarjeta_credito_nacional_transactions_staging (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    source_id INT NOT NULL,
    Fecha VARCHAR(50),
    Descripcion VARCHAR(255),
    Cuotas VARCHAR(50),
    `Monto ($)` VARCHAR(50), -- Column name with special characters
    file_hash VARCHAR(64) NOT NULL,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bctcn_meta FOREIGN KEY (metadata_id) REFERENCES document_metadata_staging(metadata_id),
    CONSTRAINT fk_bctcn_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para transacciones de tarjetas de crédito internacionales (de ingest_xls_international_cc.py)
CREATE TABLE IF NOT EXISTS banco_chile_tarjeta_credito_internacional_transactions_staging (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    source_id INT NOT NULL,
    Fecha VARCHAR(50),
    Descripcion VARCHAR(255),
    Categoria VARCHAR(100),
    Cuotas VARCHAR(50),
    `Monto Moneda Origen` VARCHAR(50), -- Column name with special characters
    `Monto (USD)` VARCHAR(50), -- Column name with special characters
    Pais VARCHAR(100),
    file_hash VARCHAR(64) NOT NULL,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bctci_meta FOREIGN KEY (metadata_id) REFERENCES document_metadata_staging(metadata_id),
    CONSTRAINT fk_bctci_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para transacciones de tarjetas de crédito Falabella (de ingest_xls_falabella_cc.py)
CREATE TABLE IF NOT EXISTS falabella_tarjeta_credito_transactions_staging (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    source_id INT NOT NULL,
    FECHA VARCHAR(50),
    DESCRIPCION VARCHAR(255),
    `VALOR CUOTA` VARCHAR(50), -- Column name with special characters
    `CUOTAS PENDIENTES` VARCHAR(50), -- Column name with special characters
    file_hash VARCHAR(64) NOT NULL,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ftc_meta FOREIGN KEY (metadata_id) REFERENCES document_metadata_staging(metadata_id),
    CONSTRAINT fk_ftc_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para transacciones de cuenta corriente Falabella (de ingest_xls_falabella_cuenta_corriente.py)
CREATE TABLE IF NOT EXISTS falabella_cuenta_corriente_transactions_staging (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    source_id INT NOT NULL,
    Fecha VARCHAR(50),
    Descripcion VARCHAR(255),
    Cargo VARCHAR(50),
    Abono VARCHAR(50),
    Saldo VARCHAR(50),
    file_hash VARCHAR(64) NOT NULL,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fcc_meta FOREIGN KEY (metadata_id) REFERENCES document_metadata_staging(metadata_id),
    CONSTRAINT fk_fcc_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para transacciones de línea de crédito Falabella (de ingest_xls_falabella_linea_credito.py)
CREATE TABLE IF NOT EXISTS falabella_linea_credito_transactions_staging (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    source_id INT NOT NULL,
    Fecha VARCHAR(50),
    Descripcion VARCHAR(255),
    Cargos VARCHAR(50),
    Abonos VARCHAR(50),
    `Monto utilizado` VARCHAR(50), -- Column name with special characters
    `Tasa diaria` VARCHAR(50), -- Column name with special characters
    Intereses VARCHAR(50),
    file_hash VARCHAR(64) NOT NULL,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_flc_meta FOREIGN KEY (metadata_id) REFERENCES document_metadata_staging(metadata_id),
    CONSTRAINT fk_flc_src FOREIGN KEY (source_id) REFERENCES fuentes(fuente_id)
);
"""

def execute_sql_script(sql_commands):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            for command in sql_commands:
                if command.strip(): # Ensure command is not empty
                    try:
                        cursor.execute(command)
                        logging.info(f"Executed SQL command: {command.strip()[:100]}...")
                    except mysql.connector.Error as err:
                        logging.error(f"Error executing SQL command: {err}")
                        conn.rollback() # Rollback on error
                        return False
            conn.commit()
            logging.info("All SQL commands executed successfully.")
            return True
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        return False

if __name__ == "__main__":
    # Split the SQL content into individual commands
    # Basic split by ';' might not handle all cases (e.g., ';' within strings)
    # but should be sufficient for simple CREATE TABLE statements.
    sql_commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
    
    if execute_sql_script(sql_commands):
        logging.info("Staging tables creation script completed.")
    else:
        logging.error("Staging tables creation script failed.")