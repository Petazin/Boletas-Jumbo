# Changelog: Zenith Finance

## [v0.5.0] - 2026-04-17
### Añadido
- **Soporte Banco Falabella**: Implementación del parser inteligente para PDFs de Banco Falabella (IA + OCR).
- **Llavero de Contraseñas (Keychain)**: Sistema de persistencia de claves para PDFs protegidos por tipo de documento.
- **Detección de Errores de Seguridad**: Identificación y reporte específico de errores de contraseña en el API.
- **Refinamiento de Fechas**: Soporte universal para formatos ISO `AAAA-MM-DD` y regionales `DD-MMM`.
- **Script de Ingesta Inteligente**: `test_ingesta.py` actualizado con soporte interactivo para contraseñas.

## [v0.4.0] - 2026-04-17
### Añadido
- **Solución OCR Integral**: Integración de Tesseract OCR (spa) como fallback automático para PDFs escaneados.
- **Extracción Multilínea**: Optimización de prompts (22+ filas corregidas).
- **Mapeo de Clasificación**: Lógica especializada para distinguir Monto vs Saldo en Banco de Chile.

## [v0.3.0] - 2026-04-15
### Añadido
- Integración de IA Local (Fase 3) mediante LM Studio.
- Sistema de OCR visual para procesamiento de PDFs escaneados.
- Categorización automática de gastos (Supermercado, Transferencias, Salud, etc.).
- Utilidad de conversión de PDF a Imagen de alta resolución.
- Sistema de prompts personalizables en archivos externos.
- Actualización de esquema de DB para soportar datos enriquecidos.
