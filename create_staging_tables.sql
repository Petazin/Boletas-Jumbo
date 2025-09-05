-- Tabla de staging para cartolas de Cuenta Corriente Banco de Chile (PDF)
CREATE TABLE IF NOT EXISTS staging_cta_corriente_banco_de_chile (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `FECHA DIA/MES` VARCHAR(255),
    `DETALLE DE TRANSACCION` VARCHAR(255),
    `SUCURSAL` VARCHAR(255),
    `N° DOCTO` VARCHAR(255),
    `MONTO CHEQUES O CARGOS` VARCHAR(255),
    `MONTO DEPOSITOS O ABONOS` VARCHAR(255),
    `SALDO` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para Tarjeta de Crédito Falabella Nacional (XLS)
CREATE TABLE IF NOT EXISTS staging_tarjeta_credito_falabella_nacional (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `FECHA` VARCHAR(255),
    `DESCRIPCION` VARCHAR(255),
    `VALOR CUOTA` VARCHAR(255),
    `CUOTAS PENDIENTES` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para Cuenta Corriente Falabella (XLS)
CREATE TABLE IF NOT EXISTS staging_cta_corriente_falabella (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `Fecha` VARCHAR(255),
    `Descripcion` VARCHAR(255),
    `Cargo` VARCHAR(255),
    `Abono` VARCHAR(255),
    `Saldo` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para Línea de Crédito Falabella (XLS)
CREATE TABLE IF NOT EXISTS staging_linea_credito_falabella (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `Fecha` VARCHAR(255),
    `Descripcion` VARCHAR(255),
    `Cargos` VARCHAR(255),
    `Abonos` VARCHAR(255),
    `Monto utilizado` VARCHAR(255),
    `Tasa diaria` VARCHAR(255),
    `Intereses` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para Tarjeta de Crédito Banco de Chile Internacional (XLS)
CREATE TABLE IF NOT EXISTS staging_tarjeta_credito_banco_de_chile_internacional (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `Fecha` VARCHAR(255),
    `Descripción` VARCHAR(255),
    `Categoría` VARCHAR(255),
    `Cuotas` VARCHAR(255),
    `Monto Moneda Origen` VARCHAR(255),
    `Monto (USD)` VARCHAR(255),
    `País` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para Tarjeta de Crédito Banco de Chile Nacional (XLS)
CREATE TABLE IF NOT EXISTS staging_tarjeta_credito_banco_de_chile_nacional (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `Fecha` VARCHAR(255),
    `Descripción` VARCHAR(255),
    `Cuotas` VARCHAR(255),
    `Monto ($)` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para Línea de Crédito Banco de Chile (XLS)
CREATE TABLE IF NOT EXISTS staging_linea_credito_banco_chile (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `Fecha` VARCHAR(255),
    `Descripcion` VARCHAR(255),
    `Cargos` VARCHAR(255),
    `Abonos` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- Tabla de staging para Línea de Crédito Banco de Chile (PDF)
CREATE TABLE IF NOT EXISTS staging_linea_credito_banco_chile_pdf (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    `FECHA DIA/MES` VARCHAR(255),
    `DETALLE DE TRANSACCION` VARCHAR(255),
    `SUCURSAL` VARCHAR(255),
    `N° DOCTO` VARCHAR(255),
    `MONTO CHEQUES O CARGOS` VARCHAR(255),
    `MONTO DEPOSITOS O ABONOS` VARCHAR(255),
    `SALDO` VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- NOTA: Las tablas tarjeta_credito_banco_de_chile_nacional_staging e internacional_staging
-- ya están definidas arriba, pero los scripts ingest_xls_national_cc.py e ingest_xls_international_cc.py 
-- deberían usar estas tablas respectivamente.

-- Tabla de staging para Boletas Jumbo (PDF)
CREATE TABLE IF NOT EXISTS staging_boletas_jumbo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    fuente_id INT NOT NULL,
    boleta_id VARCHAR(255),
    fecha_compra VARCHAR(255),
    hora_compra VARCHAR(255),
    sku VARCHAR(255),
    descripcion_producto VARCHAR(255),
    precio_total_item_str VARCHAR(255),
    cantidad_str VARCHAR(255),
    precio_unitario_str VARCHAR(255),
    descripcion_oferta VARCHAR(255),
    monto_descuento_str VARCHAR(255),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_cartolas_bancarias(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);