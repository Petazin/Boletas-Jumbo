# Zenith Finance - Contexto de IA

Este archivo sirve para que los modelos de IA (como Antigravity) entiendan rápidamente el estado actual del proyecto, sus decisiones de arquitectura y sus desafíos.

## Estado Actual (v0.6.0)
- **Hito**: Motor de Categorización Híbrido, Ingesta Masiva y soporte para Línea de Crédito (LC).
- **Estrategia**: Clasificación local por reglas + Respaldo de IA validada.
- **Seguridad**: Llavero persistente y manejo robusto de archivos vacíos/corruptos (400 Bad Request).
- **Control de Datos**: Sistema de "Escudo Anti-Saldos" que ignora activamente filas de balances para evitar transacciones fantasmas en LC.

## Arquitectura de Datos
1. **archivos_fuente**: Registro con hash SHA256 (Deduplicación activa).
2. **reglas_categorizacion**: Tabla de patrones para clasificación local instántanea.
3. **credenciales_archivadores**: Llavero local origen+tipo -> password.
4. **metadatos_documento**: Cabeceras y atributos específicos.
5. **staging**: Datos crudos por banco.
6. **transacciones_consolidadas**: Datos normalizados y categorizados (SHA256 ID único).

## Desafíos Resueltos
- **PDFs Protegidos**: Implementado soporte para contraseñas en `pdf2image` y `pdfplumber` con persistencia automática en DB tras éxito.
- **Falabella PDF Multilínea**: Motor inteligente One-Pass perfeccionado para jamás truncar descripciones separadas en varias filas visuales ni omitir el último registro del estado de cuenta.
- **Feedback de Error**: Identificación clara de errores de contraseña en el API (`PASSWORD_REQUIRED`).

## Próximos Pasos
- Implementar Parser de Boletas Jumbo (OCR especializado para tickets térmicos).
- Dashboard Frontend inicial (Vite/Next.js) para visualización de gastos y gestión de llavero.
- Refinamiento de categorización manual desde la UI.
