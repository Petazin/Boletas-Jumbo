# Zenith Finance 🏦

Sistema inteligente de ingesta y análisis de finanzas personales, diseñado para automatizar la extracción de datos desde PDFs bancarios (escaneados o digitales) y boletas de supermercado, utilizando IA Visual Local (OCR + LLM).

## Características (v0.5.0)

- **IA Visual Multimodal**: Extracción de datos sin depender de capas de texto nativas, ideal para cartolas escaneadas.
- **Estrategia Two-Pass**: Captura de metadatos ( Pass 1) y transacciones (Pass 2) para máxima precisión sin alucinaciones.
- **Soporte de PDFs Protegidos**: Sistema de **Llavero de Contraseñas (Keychain)** que recuerda las claves de tus cartolas por banco.
- **OCR Híbrido**: Integración con Poppler y Tesseract para pre-procesamiento de alta resolución.
- **Privacidad Local**: Procesamiento mediante LM Studio (host.docker.internal:1234) sin enviar datos a la nube.

## Bancos Soportados

- [x] **Banco de Chile**: Cartola de Cuenta Corriente (PDF Escaneado/Digital).
- [x] **Banco Falabella**: Cartola de Cuenta de Crédito/Corriente (PDF con Password).
- [ ] **Jumbo**: Boletas de Supermercado (OCR Térmico) - *En desarrollo*.

## Requisitos

- **Docker Desktop** (con WSL2 habilitado).
- **LM Studio** corriendo en el puerto `1234` con un modelo multimodal (ej. Llava o Gemma 2).
- **Python 3.10+** (para ejecución de scripts de prueba locales).

## Instalación Desarrollador

1. Clonar el repositorio.
2. Levantar el entorno Docker:
   ```bash
   docker-compose up -d --build
   ```
3. Ejecutar la consola de ingesta para probar:
   ```bash
   python test_ingesta.py
   ```

## Esquema de Datos

El sistema utiliza una arquitectura de 3 capas:
1. **Capa 0 (Raw)**: Almacenamiento del archivo original con hash SHA256.
2. **Capa 1 (Staging)**: Datos crudos extraídos por la IA por cada entidad emisora.
3. **Capa 2 (Consolidada)**: Datos normalizados, deduplicados y categorizados unificados.

---
*Desarrollado con ❤️ para organizar el caos financiero.*
