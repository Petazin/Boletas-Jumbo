# Contexto del Proyecto: Zenith Finance

## 1. Visión General

**Zenith Finance** es una aplicación integral de gestión de finanzas personales diseñada para proporcionar claridad total sobre el comportamiento de gasto, identificar oportunidades de ahorro y automatizar el seguimiento financiero.

## 2. Arquitectura del Sistema

- **Frontend:** React + Vite (Dashboard interactivo).
- **Backend:** FastAPI (Procesamiento de datos y API).
- **Base de Datos:** MySQL (Almacenamiento persistente con trazabilidad 360°).
- **Infraestructura:** Docker Compose.
- **Inteligencia Artificial:** LLMs con procesamiento en dos rondas (Two-Pass OCR) para aislar la abstracción de metadatos de las tablas, usando Universal JSON Metadata para acomodar cualquier institución.

## 3. Capas de Datos

1. **Originals Repository:** Archivos crudos respaldados en su formato original.
2. **Staging Layer:** Datos extraídos sin transformar por origen.
3. **Consolidated (Raw) Layer:** Transacciones unificadas con trazabilidad al origen.
4. **Item Details:** Desglose de productos (items) vinculados a transacciones (ej: Boletas Jumbo).

## 4. Principios de Arquitectura y Orden (Instrucción Fundamental)

- **Diseño antes que Acción:** Antes de crear cualquier script o aplicación, se debe diseñar una estructura de directorios lógica que evite el desorden.
- **Sentido Funcional:** Cada archivo y carpeta debe tener un propósito claro y estar ubicado según su función en la arquitectura (ej: `/core`, `/api`, `/utils`).
- **Escalabilidad:** El orden debe mantenerse incluso cuando el proyecto crezca.

## 5. Reglas del Proyecto

- Toda la comunicación y mensajes de commit deben ser en **Español**.
- Los comandos de shell deben registrarse en `agent_activity.log`.
- Siempre actualizar `GEMINI.md`, `README.md` y `CHANGELOG.md` tras cambios significativos.
- El usuario debe ejecutar los scripts y proporcionar los logs.

## 5. Roadmap Actual

- **Fase 0:** Preparación y Backup (Completado).
- [x] **Fase 2: Motor de Ingesta Modular** (Estructura Base e Ingesta inicial).
- [ ] **Fase 3: Inteligencia Artificial Local** (Implementado - En Verificación).
- [ ] **Fase 4: Frontend Premium** (Pendiente).
- **Fase 4:** Frontend Premium.
