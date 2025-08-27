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

-- Table: metadatos_cartolas_bancarias_raw
CREATE TABLE IF NOT EXISTS metadatos_cartolas_bancarias_raw (
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

-- Table: transacciones_cuenta_bancaria_raw
CREATE TABLE IF NOT EXISTS transacciones_cuenta_bancaria_raw (
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
    FOREIGN KEY (metadata_id) REFERENCES metadatos_cartolas_bancarias_raw(metadata_id)
);

-- Table: transacciones_tarjeta_credito_raw
CREATE TABLE IF NOT EXISTS transacciones_tarjeta_credito_raw (
    raw_id INT AUTO_INCREMENT PRIMARY KEY,
    fuente_id INT NOT NULL,
    metadata_id INT NOT NULL,
    fecha_transaccion_str VARCHAR(10),
    descripcion_transaccion TEXT,
    cuotas VARCHAR(10),
    monto_pesos DECIMAL(15, 2),
    linea_original_datos TEXT,
    procesado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(fuente_id),
    FOREIGN KEY (metadata_id) REFERENCES metadatos_cartolas_bancarias_raw(metadata_id)
);

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
    FOREIGN KEY (metadata_id_original) REFERENCES metadatos_cartolas_bancarias_raw(metadata_id),
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
    file_hash VARCHAR(64) UNIQUE,
    PRIMARY KEY (id)
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