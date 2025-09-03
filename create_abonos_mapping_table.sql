CREATE TABLE IF NOT EXISTS abonos_mapping (
    description VARCHAR(255) NOT NULL,
    PRIMARY KEY (description)
);

-- Insertar la descripción inicial para los pagos de tarjeta de crédito
INSERT INTO abonos_mapping (description) VALUES ('Pago Pesos TEF')
ON DUPLICATE KEY UPDATE description = description; -- No hacer nada si ya existe
