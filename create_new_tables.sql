-- ==================================================================================================
-- ARCHIVO MAESTRO DE ESQUEMA DE BASE DE DATOS
-- Este archivo contiene la definición de todas las tablas del proyecto.
-- ==================================================================================================

-- --------------------------------------------------------------------------------------------------
-- Tablas Fundamentales
-- --------------------------------------------------------------------------------------------------

-- Table: fuentes
CREATE TABLE IF NOT EXISTS fuentes (
    fuente_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_fuente VARCHAR(255) NOT NULL UNIQUE,
    tipo_fuente VARCHAR(50) -- e.g., 'Supermercado', 'Banco', 'Tarjeta de Credito', 'Inversiones'
);

-- Table: categorias_principales
CREATE TABLE IF NOT EXISTS categorias_principales (
    categoria_principal_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_categoria_principal VARCHAR(255) NOT NULL UNIQUE,
    tipo_transaccion ENUM('Ingreso', 'Gasto', 'Transferencia') NOT NULL
);

-- Table: subcategorias
CREATE TABLE IF NOT EXISTS subcategorias (
    subcategoria_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_subcategoria VARCHAR(255) NOT NULL,
    categoria_principal_id INT NOT NULL,
    FOREIGN KEY (categoria_principal_id) REFERENCES categorias_principales(categoria_principal_id),
    UNIQUE (nombre_subcategoria, categoria_principal_id)
);

-- Table: abonos_mapping
CREATE TABLE IF NOT EXISTS abonos_mapping (
    description VARCHAR(255) NOT NULL,
    PRIMARY KEY (description)
);

-- Insertar la descripción inicial para los pagos de tarjeta de crédito
INSERT INTO abonos_mapping (description) VALUES ('Pago Pesos TEF')
ON DUPLICATE KEY UPDATE description = description; -- No hacer nada si ya existe

-- --------------------------------------------------------------------------------------------------
-- Tabla de Metadatos Unificada
-- --------------------------------------------------------------------------------------------------

-- Table: raw_metadatos_documentos (RENAMED from raw_metadatos_cartolas_bancarias)
CREATE TABLE IF NOT EXISTS raw_metadatos_documentos (
    metadata_id INT AUTO_INCREMENT PRIMARY KEY,
    fuente_id INT NOT NULL,
    nombre_titular_cuenta VARCHAR(255),
    rut VARCHAR(20),
    numero_cuenta VARCHAR(50),
    moneda VARCHAR(10),
    fecha_emision_cartola DATE,
    folio_cartola VARCHAR(50),
    saldo_contable DECIMAL(15, 2),
    retenciones_24hrs DECIMAL(15, 2),
    retenciones_48hrs DECIMAL(15, 2),
    saldo_inicial DECIMAL(15, 2),
    saldo_disponible DECIMAL(15, 2),
    linea_credito DECIMAL(15, 2),
    tipo_tarjeta VARCHAR(255),
    estado_tarjeta VARCHAR(50),
    monto_facturado DECIMAL(15, 2),
    pago_minimo DECIMAL(15, 2),
    fecha_facturacion DATE,
    fecha_vencimiento DATE,
    nombre_archivo_original VARCHAR(255),
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    document_type VARCHAR(255),
    procesado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- --------------------------------------------------------------------------------------------------
-- Tablas de Staging
-- --------------------------------------------------------------------------------------------------

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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
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
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id),
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id)
);

-- --------------------------------------------------------------------------------------------------
-- Tablas Raw (Datos Crudos Consolidados)
-- --------------------------------------------------------------------------------------------------

-- Table: transacciones_cta_corriente_raw
CREATE TABLE IF NOT EXISTS raw_transacciones_cta_corriente (
    raw_id INT AUTO_INCREMENT PRIMARY KEY,
    fuente_id INT NOT NULL,
    metadata_id INT NOT NULL,
    fecha_transaccion_str VARCHAR(10),
    descripcion_transaccion TEXT,
    canal_o_sucursal VARCHAR(255),
    cargos_pesos DECIMAL(15, 2),
    abonos_pesos DECIMAL(15, 2),
    saldo_pesos DECIMAL(15, 2),
    linea_original_datos TEXT,
    procesado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id)
);

-- Table: transacciones_tarjeta_credito_nacional_raw
CREATE TABLE IF NOT EXISTS raw_transacciones_tarjeta_credito_nacional (
    raw_id INT AUTO_INCREMENT PRIMARY KEY,
    fuente_id INT NOT NULL,
    metadata_id INT NOT NULL,
    fecha_cargo_original DATE,
    fecha_cargo_cuota DATE,
    descripcion_transaccion TEXT,
    cuota_actual INT,
    total_cuotas INT,
    cargos_pesos DECIMAL(15, 2),
    abonos_pesos DECIMAL(15, 2),
    linea_original_datos TEXT,
    procesado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id)
);

-- Table: transacciones_tarjeta_credito_internacional_raw
CREATE TABLE IF NOT EXISTS raw_transacciones_tarjeta_credito_internacional (
    raw_id INT AUTO_INCREMENT PRIMARY KEY,
    fuente_id INT NOT NULL,
    metadata_id INT NOT NULL,
    fecha_cargo_original DATE,
    fecha_cargo_cuota DATE,
    descripcion_transaccion TEXT,
    categoria VARCHAR(255),
    cuota_actual INT,
    total_cuotas INT,
    cargos_pesos DECIMAL(15, 2),
    abonos_pesos DECIMAL(15, 2),
    monto_usd DECIMAL(15, 2),
    tipo_cambio DECIMAL(10, 4),
    pais VARCHAR(255),
    procesado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id),
    FOREIGN KEY (metadata_id) REFERENCES raw_metadatos_documentos(metadata_id)
);

-- Table: raw_transacciones_linea_credito
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
    CONSTRAINT `fk_linea_credito_metadata` FOREIGN KEY (`metadata_id`) REFERENCES `raw_metadatos_documentos` (`metadata_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------------------------------
-- Tablas de Negocio y Finales
-- --------------------------------------------------------------------------------------------------

-- Table: transacciones
CREATE TABLE IF NOT EXISTS transacciones (
    transaccion_id VARCHAR(255) PRIMARY KEY,
    fuente_id INT NOT NULL,
    raw_id_original INT,
    metadata_id_original INT,
    fecha_transaccion DATE NOT NULL,
    hora_transaccion TIME,
    descripcion TEXT NOT NULL,
    monto DECIMAL(15, 2) NOT NULL,
    tipo_transaccion ENUM('Ingreso', 'Gasto', 'Transferencia') NOT NULL,
    categoria_principal_id INT,
    subcategoria_id INT,
    ruta_documento_original VARCHAR(255),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id),
    FOREIGN KEY (metadata_id_original) REFERENCES raw_metadatos_documentos(metadata_id),
    FOREIGN KEY (categoria_principal_id) REFERENCES categorias_principales(categoria_principal_id),
    FOREIGN KEY (subcategoria_id) REFERENCES subcategorias(subcategoria_id)
);

-- Table: items_transaccion
CREATE TABLE IF NOT EXISTS items_transaccion (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    transaccion_id VARCHAR(255) NOT NULL,
    sku VARCHAR(255),
    descripcion_producto TEXT NOT NULL,
    cantidad DECIMAL(10, 3),
    precio_unitario DECIMAL(15, 2),
    precio_total_item DECIMAL(15, 2),
    descripcion_oferta TEXT,
    monto_descuento DECIMAL(15, 2),
    FOREIGN KEY (transaccion_id) REFERENCES transacciones(transaccion_id)
);

-- Table: historial_descargas
CREATE TABLE IF NOT EXISTS historial_descargas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL UNIQUE,
    fuente VARCHAR(50) NOT NULL,
    fecha_compra DATE,
    fecha_descarga DATETIME NOT NULL,
    nombre_archivo_original VARCHAR(255) NOT NULL,
    nuevo_nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo VARCHAR(512) NOT NULL,
    monto_total DECIMAL(10, 2),
    cantidad_items INT,
    estado VARCHAR(50) NOT NULL DEFAULT 'Descargado',
    file_hash VARCHAR(64) UNIQUE
);

-- Table: transacciones_jumbo
CREATE TABLE IF NOT EXISTS transacciones_jumbo (
    transaccion_id VARCHAR(255),
    nombre_archivo VARCHAR(255),
    fecha_compra DATE,
    hora_compra TIME,
    sku VARCHAR(255),
    cantidad INT,
    precio_unitario DECIMAL(15, 2),
    cantidad_X_precio_unitario VARCHAR(255),
    descripcion_producto TEXT,
    precio_total_item DECIMAL(15, 2),
    descripcion_oferta TEXT,
    monto_descuento DECIMAL(15, 2),
    categoria VARCHAR(255),
    PRIMARY KEY (transaccion_id, sku)
);