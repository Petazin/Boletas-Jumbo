# Zenith Finance - Contexto de IA

Este archivo sirve para que los modelos de IA (como Antigravity) entiendan rápidamente el estado actual del proyecto, sus decisiones de arquitectura y sus desafíos.

## Estado Actual (v0.5.1)
- **Hito**: Consolidación total de la ingesta para Falabella ("One-Pass" OCR Multilineal) y limpieza robusta de entorno de base de datos.
- **Estrategia**: Extracción Híbrida IA + OCR + Gestión de Credenciales.
- **Seguridad**: Los PDFs protegidos se manejan mediante un llavero local que persiste las claves por cada tipo de documento.

## Arquitectura de Datos
1. **archivos_fuente**: Registro de cada archivo subido con su hash único.
2. **credenciales_archivadores**: Llavero local que asocia `origen + tipo_documento` con su contraseña respectiva.
3. **metadatos_documento**: Almacena cabeceras (Titular, Cuenta, Período) y un JSON flexible para atributos específicos del banco.
4. **staging**: Tablas específicas por banco (`staging_banco_chile`, `staging_falabella`).
5. **transacciones_consolidadas**: Datos limpios, categorizados y con un `transaccion_id` único (SHA256).

## Desafíos Resueltos
- **PDFs Protegidos**: Implementado soporte para contraseñas en `pdf2image` y `pdfplumber` con persistencia automática en DB tras éxito.
- **Falabella PDF Multilínea**: Motor inteligente One-Pass perfeccionado para jamás truncar descripciones separadas en varias filas visuales ni omitir el último registro del estado de cuenta.
- **Feedback de Error**: Identificación clara de errores de contraseña en el API (`PASSWORD_REQUIRED`).

## Próximos Pasos
- Implementar Parser de Boletas Jumbo (OCR especializado para tickets térmicos).
- Dashboard Frontend inicial (Vite/Next.js) para visualización de gastos y gestión de llavero.
- Motor de categorización basado en reglas y IA.
