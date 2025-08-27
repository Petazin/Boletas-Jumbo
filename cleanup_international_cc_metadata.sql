-- Limpia los metadatos de las cartolas de Tarjeta de Crédito Internacional para forzar su reprocesamiento.
-- Esto es necesario porque las ejecuciones anteriores fallaron después de insertar los metadatos pero antes de insertar las transacciones.

DELETE FROM bank_statement_metadata_raw
WHERE document_type = 'International Credit Card Statement';
