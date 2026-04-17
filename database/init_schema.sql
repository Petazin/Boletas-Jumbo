-- Configuración de Codificación
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- --------------------------------------------------------------------------------------------------
-- CAPA 0: GESTIÓN DE ARCHIVOS (TRAZABILIDAD)
-- --------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS archivos_fuente (
    archivo_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_original VARCHAR(255) NOT NULL,
    nombre_almacenamiento VARCHAR(255) NOT NULL,
    hash_archivo VARCHAR(64) UNIQUE NOT NULL, -- Para evitar duplicados de archivos
    tipo_documento ENUM('Cartola_CC', 'Cartola_TC', 'Boleta_Supermercado', 'Otro') NOT NULL,
    origen ENUM('Banco_Chile', 'Falabella', 'Jumbo', 'Lider', 'Otro') NOT NULL,
    extension VARCHAR(10) NOT NULL,
    tamano_bytes BIGINT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ruta_backup VARCHAR(512) NOT NULL,
    estado_procesamiento ENUM('Cargado', 'En_Proceso', 'Completado', 'Error') DEFAULT 'Cargado'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------------------------------
-- TABLA DE METADATOS UNIVERSALES (Capa 0.5)
-- --------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS metadatos_documento (
    metadata_id INT AUTO_INCREMENT PRIMARY KEY,
    archivo_id INT NOT NULL,
    entidad_emisora VARCHAR(100),
    titular VARCHAR(255),
    identificador_cuenta VARCHAR(100), 
    periodo_desde DATE,
    periodo_hasta DATE,
    atributos_adicionales JSON, 
    FOREIGN KEY (archivo_id) REFERENCES archivos_fuente(archivo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------------------------------
-- CAPA 1: STAGING (DATOS CRUDOS POR ORIGEN)
-- --------------------------------------------------------------------------------------------------

-- Staging para Banco de Chile (Ejemplo: Línea de Crédito / CC)
CREATE TABLE IF NOT EXISTS staging_banco_chile (
    staging_id INT AUTO_INCREMENT PRIMARY KEY,
    archivo_id INT NOT NULL,
    fecha_texto VARCHAR(100),
    descripcion_cruda TEXT,
    monto_cargo_crudo VARCHAR(100),
    monto_abono_crudo VARCHAR(100),
    FOREIGN KEY (archivo_id) REFERENCES archivos_fuente(archivo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Staging para Falabella (Ejemplo: XLS/PDF)
CREATE TABLE IF NOT EXISTS staging_falabella (
    staging_id INT AUTO_INCREMENT PRIMARY KEY,
    archivo_id INT NOT NULL,
    fecha_texto VARCHAR(100),
    descripcion_cruda TEXT,
    cuotas VARCHAR(50),
    monto_pesos_crudo VARCHAR(100),
    monto_usd_crudo VARCHAR(100),
    FOREIGN KEY (archivo_id) REFERENCES archivos_fuente(archivo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------------------------------
-- CAPA 2: CONSOLIDADA (EL DATO "LIMPIO" Y UNIFICADO)
-- --------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS categorias_principales (
    categoria_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    color_hex VARCHAR(7) -- Para el diseño premium en el frontend
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transacciones_consolidadas (
    transaccion_id VARCHAR(64) PRIMARY KEY, -- Hash o UUID único de la transacción
    archivo_id INT NOT NULL,
    fecha_transaccion DATE NOT NULL,
    descripcion_limpia VARCHAR(255) NOT NULL,
    monto DECIMAL(15, 2) NOT NULL,
    tipo ENUM('Ingreso', 'Gasto', 'Transferencia') NOT NULL,
    categoria_id INT,
    subcategoria VARCHAR(100),
    comentario TEXT,
    es_gasto_innecesario BOOLEAN DEFAULT FALSE,
    fue_clasificado_por_ia BOOLEAN DEFAULT FALSE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (archivo_id) REFERENCES archivos_fuente(archivo_id),
    FOREIGN KEY (categoria_id) REFERENCES categorias_principales(categoria_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------------------------------
-- CAPA 3: DETALLE DE ITEMS (ITEMS DE BOLETAS)
-- --------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS items_compra (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    transaccion_id VARCHAR(64) NOT NULL,
    archivo_id INT, -- Referencia a la boleta específica si existe
    sku VARCHAR(100),
    producto VARCHAR(255) NOT NULL,
    cantidad DECIMAL(10, 3) DEFAULT 1,
    precio_unitario DECIMAL(15, 2),
    precio_total DECIMAL(15, 2),
    descuento DECIMAL(15, 2) DEFAULT 0,
    categoria_item VARCHAR(100), -- Categoría específica del producto (ej: Lácteos)
    FOREIGN KEY (transaccion_id) REFERENCES transacciones_consolidadas(transaccion_id),
    FOREIGN KEY (archivo_id) REFERENCES archivos_fuente(archivo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------------------------------
-- PERFILADO Y SUGERENCIAS
-- --------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS perfil_usuario (
    perfil_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_perfil VARCHAR(100), -- ej: "Equilibrio", "Ahorrador"
    descripcion TEXT,
    fecha_analisis DATE,
    metrics_json JSON -- Métricas complejas detectadas por IA
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sugerencias_ahorro (
    sugerencia_id INT AUTO_INCREMENT PRIMARY KEY,
    tipo ENUM('Reduccion_Gasto', 'Eliminacion_Suscripcion', 'Mejora_Habito', 'Alerta_Precio') NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT NOT NULL,
    monto_estimado_ahorro DECIMAL(15, 2),
    estado ENUM('Pendiente', 'Aceptada', 'Rechazada', 'Cumplida') DEFAULT 'Pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------------------------------
-- DATOS INICIALES
-- --------------------------------------------------------------------------------------------------

INSERT INTO categorias_principales (nombre, color_hex) VALUES 
('Alimentación/Supermercado', '#FF5733'),
('Vivienda y Servicios', '#3357FF'),
('Transporte', '#33FF57'),
('Salud', '#FF33A1'),
('Ocio y Entretenimiento', '#F3FF33'),
('Educación', '#A133FF'),
('Impuestos y Tasas', '#8B4513'),
('Otros', '#808080');

SET FOREIGN_KEY_CHECKS = 1;
