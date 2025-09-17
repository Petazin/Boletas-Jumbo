# Proyecto de Finanzas Personales

## Visión General del Proyecto

El objetivo final de este proyecto es construir una aplicación integral para la gestión de finanzas personales. Esta aplicación permitirá a los usuarios tener un control total sobre sus ingresos y gastos de forma automatizada, conectándose a diversas fuentes (bancos, tiendas), procesando la información, categorizándola inteligentemente y presentándola en un dashboard interactivo con alertas y presupuestos.

El desarrollo se ha dividido en dos fases principales:

1.  **Fase 1 (Completada):** Perfeccionar un motor de análisis de boletas de supermercado (Jumbo) para extraer y analizar datos de consumo de forma automatizada.
2.  **Fase 2 (En progreso):** Expandir la aplicación a un gestor financiero completo, con capacidad para procesar múltiples tipos de documentos (boletas, cartolas bancarias en PDF y XLS), controlar gastos e ingresos, y ayudar a mantener un presupuesto mensual saludable.

---

## Arquitectura y Módulos del Proyecto

El proyecto ha sido reestructurado en una arquitectura modular dentro del directorio `src`, facilitando la mantenibilidad y escalabilidad.

*   **`src/`**: Contiene todo el código fuente de la aplicación.
    *   **`config.py`**: Módulo central de configuración con constantes, credenciales, rutas y expresiones regulares.
    *   **`run_pipeline.py`**: Script orquestador principal que ejecuta todo el flujo de ingesta de datos.
    *   **`core/`**: Contiene la lógica de negocio principal.
        *   `pdf_parser.py`: Módulo de extracción y parsing para boletas de supermercado en PDF.
        *   `product_categorizer.py`: Módulo de lógica de negocio para categorizar productos.
    *   **`db/`**: Módulos relacionados con la base de datos.
        *   `database_utils.py`: Utilidad para la gestión centralizada de la conexión a la base de datos.
        *   `reset_database.py`: Script para resetear la base de datos a su estado inicial.
    *   **`ingestion/`**: Contiene todos los scripts para la ingesta de datos desde diferentes fuentes.
        *   `download_boletas.py`: Automatización para descargar boletas de Jumbo.cl.
        *   `process_boletas.py`: Orquestador que procesa los PDFs de boletas en paralelo.
        *   `ingest_*.py`: Scripts especializados para procesar cartolas bancarias y de tarjetas de crédito desde archivos PDF y XLS.
    *   **`utils/`**: Módulos de utilidad.
        *   `file_utils.py`: Utilidades para la gestión de archivos y logging de movimientos.
*   **`fuentes/`**: Directorio raíz para los archivos de datos a ser procesados (anteriormente `descargas`).
*   **`cuarentena/`**: Directorio para archivos que no pudieron ser procesados.
*   **`tests/`**: Directorio de pruebas unitarias con `pytest`.

### Capa de Staging de Datos

La capa de staging es un componente fundamental de la arquitectura de ingesta de datos, diseñada para capturar los datos extraídos de los documentos en su formato original antes de cualquier transformación o consolidación.

*   **Propósito:** Asegurar la visibilidad, trazabilidad y validación de los datos crudos extraídos.
*   **Nomenclatura:** Las tablas de staging siguen una convención `staging_[tipo_documento]_[origen]` (ej. `staging_cta_corriente_banco_de_chile`, `staging_tarjeta_credito_falabella_nacional`). Esto permite una clara identificación del tipo de dato y su fuente.
*   **Estructura:** Cada tabla de staging replica la estructura de los datos tal como son extraídos del documento fuente, preservando la información original.
*   **Validación Post-Ingesta:** Para garantizar la integridad de los datos, cada script de ingesta realiza una validación inmediata después de cargar los datos en la tabla de staging. Se verifica que el **conteo de registros** y la **suma total de montos** extraídos del archivo coincidan exactamente con los datos insertados en la base de datos, registrando el resultado de esta validación en el log.
*   **Rol en el ETL:** Las tablas de staging actúan como una fuente de datos verificada y estandarizada para las tablas raw del sistema, donde los datos de diferentes orígenes se consolidan y transforman para el análisis.

### Esquema de la Base de Datos

El proyecto utiliza un esquema de base de datos escalable y completamente en español para manejar diversos tipos de transacciones. Además de las tablas principales como `fuentes`, `categorias_principales`, `subcategorias`, `raw_metadatos_documentos`, `raw_transacciones_cta_corriente`, `raw_transacciones_tarjeta_credito_nacional`, `raw_transacciones_tarjeta_credito_internacional`, `transacciones`, `items_transaccion`, `historial_descargas` y `transacciones_jumbo`, el esquema ahora incluye una **capa de tablas de staging** dedicada para la ingesta de datos crudos. Para el esquema completo, consulta el archivo `create_new_tables.sql`.

Una tabla de soporte importante es `abonos_mapping`, que contiene descripciones de transacciones que deben ser tratadas como pagos (abonos) en las tarjetas de crédito, permitiendo una correcta clasificación de los flujos de dinero.

---

## Uso Detallado y Flujos de Trabajo

El sistema se opera principalmente a través del script orquestador `run_pipeline.py`.

### Flujo Principal: Ejecución del Pipeline Completo

Para ejecutar todo el proceso de ingesta de datos de forma automatizada, utiliza el siguiente comando desde la raíz del proyecto:

```bash
python src/run_pipeline.py
```

Este script ejecutará en orden los siguientes pasos:
1.  **Reseteo de la Base de Datos:** Limpia y recrea la base de datos desde cero (opcional, configurable en el script).
2.  **Descarga de Boletas:** Inicia el proceso de descarga de boletas de Jumbo.cl (requiere intervención manual para el login).
3.  **Procesamiento de Boletas:** Procesa las boletas descargadas.
4.  **Procesamiento de Cartolas:** Ejecuta todos los scripts de ingesta para los diferentes tipos de cartolas bancarias y de tarjetas de crédito (PDF y XLS).

### Ejecución de Scripts Individuales (Para Depuración)

Si bien el pipeline principal es la forma recomendada de operar, los scripts individuales pueden ejecutarse para propósitos de depuración:

```bash
# Ejemplo: Ejecutar solo la ingesta de tarjetas de crédito nacionales
python src/ingestion/ingest_xls_national_cc.py
```

---



## Avances y Roadmap

### Fase 1: Motor de Boletas (Completada)

Se ha completado un motor robusto para el análisis de boletas de Jumbo, incluyendo:
*   Centralización de la configuración.
*   Sistema de cuarentena para PDFs con errores.
*   Pruebas unitarias con `pytest`.
*   Optimización con `multiprocessing` para el procesamiento de boletas.

### Fase 2: Gestor Financiero Integral (En Progreso)

Se está trabajando en expandir la aplicación a un gestor financiero completo.

*   `[x]` **Mejora en la Estructura de Carpetas para Estados de Cuenta Bancarios:** Se ha implementado un sistema para mover automáticamente los archivos de estados de cuenta bancarios procesados a una subcarpeta `procesados/` dentro de su directorio de origen, formalizando su estado y manteniendo los directorios de descarga limpios. Se ha añadido un sistema de logging centralizado para los movimientos de archivos.
*   `[x]` **Implementación de Hashing para Boletas de Jumbo:** Se ha implementado un mecanismo de hashing para las boletas de Jumbo, asegurando que no se procesen archivos duplicados y mejorando la integridad de los datos.
*   `[x]` **Traducción de la Base de Datos al Español:** Se ha traducido completamente el esquema de la base de datos (tablas y columnas) al español para facilitar la comprensión y el mantenimiento.
*   `[x]` **Diseño de Base de Datos Escalable:** Se ha definido un esquema de base de datos más robusto y modular.
*   `[x]` **Ingesta de Cartolas Bancarias (PDF):** Se ha implementado un sistema robusto para procesar cartolas en PDF del Banco de Chile, con detección de duplicados por contenido (hash), utilizando el campo `document_type` y moviendo los archivos procesados.
*   `[x]` **Ingesta de Cartolas Bancarias (XLS):** Se ha implementado un sistema robusto para procesar cartolas de tarjeta de crédito en XLS, incluyendo manejo de cuotas y fechas de cargo/originales, utilizando el campo `document_type` y moviendo los archivos procesados.
*   `[x]` **Expandir Ingesta de Cartolas (PDF/XLS):** Implementada la ingesta de cartolas de tarjeta de crédito nacional e internacional (XLS), con soporte para `document_type` y movimiento de archivos procesados.
*   `[x]` **Aplicar Hashing a Todos los Archivos Analizados:** Asegurado que cualquier archivo que se ingrese a la base de datos (no solo PDFs) tenga su hash para identificación única, con soporte para `document_type` y movimiento de archivos procesados.
*   `[x]` **Revisar y Validar Esquema de BD:** Confirmado que el esquema actual (`create_new_tables.sql`) es adecuado para el escalamiento y las necesidades futuras, y se han realizado ajustes en `alter_table.py` para su compatibilidad.
*   `[x]` **Implementar capa de staging para datos extraídos de archivos:** Se ha definido la arquitectura y los principios para la capa de staging, incluyendo la creación de tablas por tipo de documento/origen con la estructura original de los datos extraídos, antes de cualquier manipulación o transformación. (Esta tarea ahora se detalla en la sección "Capa de Staging de Datos" de este README y en la sección 2.2 de GEMINI.md)
*   `[ ]` **Extracción de Datos de Diferentes Dominios:** Implementar la lógica para extraer información de los distintos dominios web donde se publican las cartolas.
*   `[x]` **Renombrar Archivos Procesados:** Implementado un sistema para renombrar los archivos PDF/XLS procesados con un formato estandarizado: `[FechaProcesamiento]_[TipoDocumento]_[PeriodoDocumento]_[HashCorto].[Extension]`.
*   `[ ]` **Implementar Ingestión Robusta de XLS:** Re-evaluar o mejorar el mecanismo de parsing para archivos XLS de bancos.
*   `[ ]` **Procesamiento de Datos Bancarios:** Implementar la lógica para transformar los datos crudos de las tablas de staging a las tablas raw consolidadas, y posteriormente a la tabla `transactions` para análisis final. (Esta tarea ahora se detalla en la sección "Capa de Staging de Datos" de este README y en la sección 2.2 de los archivos de contexto de IA)
*   `[ ]` **Manejo de Duplicados y Actualizaciones (Nivel Transacción):** Implementar lógica para identificar y manejar transacciones individuales duplicadas.
*   `[ ]` **Optimización de Consultas:** Revisar y optimizar las consultas SQL para asegurar un rendimiento eficiente.
*   `[ ]` **Estrategia de Backup y Recuperación:** Definir e implementar una estrategia de backup y recuperación para la base de datos.

### Fase 2.1: Mejoras de Arquitectura y Robustez del Proceso de Ingesta
*   `[x]` **Manejo Transaccional de la Ingesta:** Modificar todos los scripts para que el `hash` de un archivo se guarde en la base de datos únicamente si el archivo y **todas** sus transacciones han sido procesadas e insertadas con éxito. Esto evitará registros "huérfanos" que impiden el reprocesamiento.
*   `[x]` **Reubicación Inteligente de Archivos:** Mejorar la lógica de movimiento de archivos para que al pasar un documento a la carpeta `procesados/` dentro de su directorio de origen, se conserve su estructura de carpetas original. Esto facilitará los ciclos de prueba y la re-ingesta manual de datos, y se complementa con un logging centralizado de movimientos de archivos.

### Fase 3: Sistema Genérico de Ingesta de Documentos (Planificada)
*   `[ ]` **Implementar Sistema Genérico de Ingesta:** Desarrollar un sistema capaz de procesar cualquier tipo de PDF o documento estructurado, inferir su esquema y mapearlo a la base de datos de forma flexible.