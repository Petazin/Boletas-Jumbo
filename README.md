# Proyecto de Finanzas Personales

## Visión General del Proyecto

El objetivo final de este proyecto es construir una aplicación integral para la gestión de finanzas personales. Esta aplicación permitirá a los usuarios tener un control total sobre sus ingresos y gastos de forma automatizada, conectándose a diversas fuentes (bancos, tiendas), procesando la información, categorizándola inteligentemente y presentándola en un dashboard interactivo con alertas y presupuestos.

El desarrollo se ha dividido en dos fases principales:

1.  **Fase 1 (Completada):** Perfeccionar un motor de análisis de boletas de supermercado (Jumbo) para extraer y analizar datos de consumo de forma automatizada.
2.  **Fase 2 (En progreso):** Expandir la aplicación a un gestor financiero completo, con capacidad para procesar múltiples tipos de documentos (boletas, cartolas bancarias en PDF y XLS), controlar gastos e ingresos, y ayudar a mantener un presupuesto mensual saludable.

---

## Arquitectura y Módulos del Proyecto

El proyecto sigue una arquitectura modular, donde cada archivo tiene una responsabilidad única, facilitando la mantenibilidad y escalabilidad:

*   **`config.py`**: Módulo central de configuración con constantes, credenciales, rutas y expresiones regulares.
*   **`database_utils.py`**: Utilidad para la gestión centralizada de la conexión a la base de datos MySQL.
*   **`ingest_pdf_bank_statement.py`**: Script para procesar cartolas bancarias en formato PDF. Extrae transacciones de múltiples archivos, calcula un hash único para cada uno para evitar duplicados y los inserta en la base de datos.
*   **`ingest_xls_national_cc.py`**: Script para procesar cartolas de tarjeta de crédito nacional en formato XLS. Extrae transacciones, calcula un hash único para evitar duplicados y los inserta en la base de datos.
*   **`ingest_xls_international_cc.py`**: Script para procesar cartolas de tarjeta de crédito internacional en formato XLS.
*   **`ingest_xls_falabella_cc.py`**: Script para procesar cartolas de tarjeta de crédito de Banco Falabella en formato XLS.
*   **`ingest_xls_falabella_cuenta_corriente.py`**: Script para procesar cartolas de cuenta corriente de Banco Falabella en formato XLS.
*   **`ingest_xls_falabella_linea_credito.py`**: Script para procesar cartolas de línea de crédito de Banco Falabella en formato XLS.

*   **`product_categorizer.py`**: Módulo de lógica de negocio para categorizar productos de boletas.
*   **`pdf_parser.py`**: Módulo de extracción y parsing para boletas de supermercado en PDF.
*   **`download_boletas.py`**: Script de automatización para descargar boletas de Jumbo.cl.
*   **`process_boletas.py`**: Script orquestador que procesa los PDFs de boletas de supermercado en paralelo.
*   **`export_data.py`**: Script para exportar datos de boletas a un archivo CSV.
*   **`utils/db/`**: Directorio con scripts de utilidad para la base de datos (resetear, configurar tablas, etc.).
*   **`utils/file_utils.py`**: Módulo de utilidades para la gestión de archivos, incluyendo el logging centralizado de movimientos de archivos.
*   **`cuarentena_pdfs/`**: Directorio para PDFs de boletas que no pudieron ser procesados.
*   **`descargas/`**: Directorio que contiene las subcarpetas para los archivos descargados de `Jumbo` y `Banco`. Dentro de estas subcarpetas, los archivos procesados se moverán a una subcarpeta `procesados/`.
*   **`tests/`**: Directorio de pruebas unitarias con `pytest`.

### Esquema de la Base de Datos

El proyecto utiliza un esquema de base de datos escalable y completamente en español para manejar diversos tipos de transacciones. Las tablas principales incluyen `fuentes`, `categorias_principales`, `subcategorias`, `metadatos_cartolas_bancarias_raw`, `transacciones_cuenta_bancaria_raw`, `transacciones_tarjeta_credito_raw`, `transacciones`, `items_transaccion`, `historial_descargas` y `transacciones_jumbo`. Para el esquema completo, consulta el archivo `create_new_tables.sql`.

Una tabla de soporte importante es `abonos_mapping`, que contiene descripciones de transacciones que deben ser tratadas como pagos (abonos) en las tarjetas de crédito, permitiendo una correcta clasificación de los flujos de dinero.

---

## Uso Detallado y Flujos de Trabajo

El sistema tiene dos flujos de trabajo principales:

### Flujo 1: Procesamiento de Boletas de Supermercado

1.  **Descargar Boletas (`download_boletas.py`):**
    ```bash
    python download_boletas.py
    ```
    Inicia sesión manualmente en Jumbo.cl cuando Selenium abra Chrome. El script descargará las boletas, calculará su hash SHA-256 y registrará los archivos en `historial_descargas`.

2.  **Procesar Boletas (`process_boletas.py`):**
    ```bash
    python process_boletas.py
    ```
    Lee los PDFs descargados, extrae los datos de productos y los guarda en la base de datos. Utiliza el hash del archivo para evitar el reprocesamiento de duplicados y mueve a cuarentena los que fallan.

### Flujo 2: Procesamiento de Cartolas Bancarias (PDF y XLS)

1.  **Descargar Cartolas (Manual):**
    Descarga tus cartolas o estados de cuenta en formato PDF o XLS y guárdalos en el directorio correspondiente (ej. `descargas/Banco/banco de chile/cuenta corriente/` para PDFs, o `descargas/Banco/banco de chile/tarjeta de credito/nacional/` para XLS).

2.  **Procesar Cartolas PDF (`ingest_pdf_bank_statement.py`):**
    ```bash
    python ingest_pdf_bank_statement.py
    ```
    *   **Proceso:** El script buscará todos los archivos PDF en el directorio configurado. Para cada archivo, calculará un hash único, verificará duplicados y, si es nuevo, lo procesará y guardará las transacciones en la base de datos. Los archivos procesados se moverán a una subcarpeta `procesados/` dentro de su directorio de origen.

3.  **Procesar Cartolas Nacionales XLS (`ingest_xls_national_cc.py`):**
    ```bash
    python ingest_xls_national_cc.py
    ```
    *   **Proceso:** Similar al procesamiento de PDFs, este script buscará archivos XLS/XLSX en el directorio configurado para cartolas nacionales. Identificará dinámicamente la cabecera de las transacciones, extraerá los datos (incluyendo el manejo de cuotas y fechas de cargo/originales) y los insertará en la base de datos, evitando duplicados por hash. Los archivos procesados se moverán a una subcarpeta `procesados/` dentro de su directorio de origen.

4.  **Procesar Cartolas Internacionales XLS (`ingest_xls_international_cc.py`):**
    ```bash
    python ingest_xls_international_cc.py
    ```
    *   **Proceso:** Similar a los otros scripts de ingesta de XLS, procesa las cartolas de tarjetas de crédito internacionales. Los archivos procesados se moverán a una subcarpeta `procesados/` dentro de su directorio de origen.

5.  **Procesar Cartolas de Banco Falabella (XLS):**
    ```bash
    # Para Tarjeta de Crédito
    python ingest_xls_falabella_cc.py

    # Para Cuenta Corriente
    python ingest_xls_falabella_cuenta_corriente.py

    # Para Línea de Crédito
    python ingest_xls_falabella_linea_credito.py
    ```
    *   **Proceso:** Cada uno de estos scripts está especializado en un producto de Banco Falabella, buscando los archivos en su directorio correspondiente y guardando los datos en la tabla apropiada. Los archivos procesados se moverán a una subcarpeta `procesados/` dentro de su directorio de origen.

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
*   `[ ]` **Extracción de Datos de Diferentes Dominios:** Implementar la lógica para extraer información de los distintos dominios web donde se publican las cartolas.
*   `[ ]` **Renombrar Archivos Procesados:** Implementar un sistema para renombrar los archivos PDF/XLS procesados con un formato estandarizado (ej. `[TipoDocumento]_[Cuenta]_[Fecha]_[HashCorto].pdf`).
*   `[ ]` **Implementar Ingestión Robusta de XLS:** Re-evaluar o mejorar el mecanismo de parsing para archivos XLS de bancos.
*   `[ ]` **Procesamiento de Datos Bancarios:** Implementar la lógica para transformar los datos crudos de `bank_account_transactions_raw` y `credit_card_transactions_raw` a la tabla `transactions`.
*   `[ ]` **Manejo de Duplicados y Actualizaciones (Nivel Transacción):** Implementar lógica para identificar y manejar transacciones individuales duplicadas.
*   `[ ]` **Optimización de Consultas:** Revisar y optimizar las consultas SQL para asegurar un rendimiento eficiente.
*   `[ ]` **Estrategia de Backup y Recuperación:** Definir e implementar una estrategia de backup y recuperación para la base de datos.

### Fase 2.1: Mejoras de Arquitectura y Robustez del Proceso de Ingesta
*   `[x]` **Manejo Transaccional de la Ingesta:** Modificar todos los scripts para que el `hash` de un archivo se guarde en la base de datos únicamente si el archivo y **todas** sus transacciones han sido procesadas e insertadas con éxito. Esto evitará registros "huérfanos" que impiden el reprocesamiento.
*   `[x]` **Reubicación Inteligente de Archivos:** Mejorar la lógica de movimiento de archivos para que al pasar un documento a la carpeta `procesados/` dentro de su directorio de origen, se conserve su estructura de carpetas original. Esto facilitará los ciclos de prueba y la re-ingesta manual de datos, y se complementa con un logging centralizado de movimientos de archivos.

### Fase 3: Sistema Genérico de Ingesta de Documentos (Planificada)
*   `[ ]` **Implementar Sistema Genérico de Ingesta:** Desarrollar un sistema capaz de procesar cualquier tipo de PDF o documento estructurado, inferir su esquema y mapearlo a la base de datos de forma flexible.