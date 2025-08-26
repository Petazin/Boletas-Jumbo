# Proyecto de Finanzas Personales

## Visión General del Proyecto

El objetivo final de este proyecto es construir una aplicación integral para la gestión de finanzas personales. Esta aplicación permitirá a los usuarios tener un control total sobre sus ingresos y gastos de forma automatizada, conectándose a diversas fuentes (bancos, tiendas), procesando la información, categorizándola inteligentemente y presentándola en un dashboard interactivo con alertas y presupuestos.

El desarrollo se ha dividido en dos fases principales:

1.  **Fase 1 (Completada):** Perfeccionar un motor de análisis de boletas de supermercado (Jumbo) para extraer y analizar datos de consumo de forma automatizada.
2.  **Fase 2 (En progreso):** Expandir la aplicación para que sea un gestor financiero completo, capaz de procesar múltiples tipos de documentos (boletas, cartolas bancarias), controlar gastos e ingresos, y ayudar a mantener un presupuesto mensual saludable.

---

## Arquitectura y Módulos del Proyecto

El proyecto sigue una arquitectura modular, donde cada archivo tiene una responsabilidad única, facilitando la mantenibilidad y escalabilidad:

*   **`config.py`**: Módulo central de configuración con constantes, credenciales, rutas y expresiones regulares.
*   **`database_utils.py`**: Utilidad para la gestión centralizada de la conexión a la base de datos MySQL.
*   **`ingest_pdf_bank_statement.py`**: Script para procesar cartolas bancarias en formato PDF. Extrae transacciones de múltiples archivos, calcula un hash único para cada uno para evitar duplicados y los inserta en la base de datos.
*   **`ingest_xls_bank_statement.py`**: **(Nuevo)** Script para procesar cartolas bancarias en formato XLS. Extrae transacciones de múltiples archivos, calcula un hash único para cada uno para evitar duplicados y los inserta en la base de datos.
*   **`product_categorizer.py`**: Módulo de lógica de negocio para categorizar productos de boletas.
*   **`pdf_parser.py`**: Módulo de extracción y parsing para boletas de supermercado en PDF.
*   **`download_boletas.py`**: Script de automatización para descargar boletas de Jumbo.cl.
*   **`process_boletas.py`**: Script orquestador que procesa los PDFs de boletas de supermercado en paralelo.
*   **`export_data.py`**: Script para exportar datos de boletas a un archivo CSV.
*   **`cuarentena_pdfs/`**: Directorio para PDFs de boletas que no pudieron ser procesados.
*   **`descargas/`**: Directorio que contiene las subcarpetas para los archivos descargados de `Jumbo` y `Banco`.
*   **`tests/`**: Directorio de pruebas unitarias con `pytest`.

### Esquema de la Base de Datos

El proyecto utiliza un esquema de base de datos escalable para manejar diversos tipos de transacciones. Las tablas principales incluyen `sources`, `main_categories`, `sub_categories`, `bank_statement_metadata_raw`, `bank_account_transactions_raw`, `credit_card_transactions_raw`, `transactions`, y `transaction_items`. Para el esquema completo, consulta el archivo `create_new_tables.sql`.

---

## Uso Detallado y Flujos de Trabajo

El sistema tiene dos flujos de trabajo principales:

### Flujo 1: Procesamiento de Boletas de Supermercado

1.  **Descargar Boletas (`download_boletas.py`):**
    ```bash
    python download_boletas.py
    ```
    Inicia sesión manualmente en Jumbo.cl cuando Selenium abra Chrome. El script descargará las boletas y registrará los archivos en `download_history`.

2.  **Procesar Boletas (`process_boletas.py`):**
    ```bash
    python process_boletas.py
    ```
    Lee los PDFs descargados, extrae los datos de productos y los guarda en la base de datos, moviendo a cuarentena los que fallan.

### Flujo 2: Procesamiento de Cartolas Bancarias (PDF y XLS)

1.  **Descargar Cartolas (Manual):**
    Descarga tus cartolas o estados de cuenta en formato PDF o XLS y guárdalos en el directorio correspondiente (ej. `descargas/Banco/banco de chile/cuenta corriente/` para PDFs, o `descargas/Banco/banco de chile/tarjeta de credito/nacional/` para XLS).

2.  **Procesar Cartolas PDF (`ingest_pdf_bank_statement.py`):**
    ```bash
    python ingest_pdf_bank_statement.py
    ```
    *   **Proceso:** El script buscará todos los archivos PDF en el directorio configurado. Para cada archivo, calculará un hash único, verificará duplicados y, si es nuevo, lo procesará y guardará las transacciones en la base de datos.

3.  **Procesar Cartolas XLS (`ingest_xls_bank_statement.py`):**
    ```bash
    python ingest_xls_bank_statement.py
    ```
    *   **Proceso:** Similar al procesamiento de PDFs, este script buscará archivos XLS/XLSX en el directorio configurado. Identificará dinámicamente la cabecera de las transacciones, extraerá los datos (incluyendo el manejo de cuotas y fechas de cargo/originales) y los insertará en la base de datos, evitando duplicados por hash.

---

## Avances y Roadmap

### Fase 1: Motor de Boletas (Completada)

Se ha completado un motor robusto para el análisis de boletas de Jumbo, incluyendo:
*   Centralización de la configuración.
*   Sistema de cuarentena para PDFs con errores.
*   Pruebas unitarias con `pytest`.
*   Optimización con `multiprocessing`.

### Fase 2: Gestor Financiero Integral (En Progreso)

Se está trabajando en expandir la aplicación a un gestor financiero completo.

*   `[x]` **Diseño de Base de Datos Escalable:** Se ha definido un esquema de base de datos más robusto y modular.
*   `[x]` **Ingesta de Cartolas Bancarias (PDF):** Se ha implementado un sistema robusto para procesar cartolas en PDF del Banco de Chile, con detección de duplicados por contenido (hash).
*   `[x]` **Ingesta de Cartolas Bancarias (XLS):** Se ha implementado un sistema robusto para procesar cartolas de tarjeta de crédito en XLS, incluyendo manejo de cuotas y fechas de cargo/originales.
*   `[ ]` **Expandir Ingesta de Cartolas PDF:** Incluir las cartolas de tarjeta de crédito (nacional e internacional) y la línea de crédito de la cuenta corriente del Banco de Chile.
*   `[ ]` **Aplicar Hashing a Todos los Archivos Analizados:** Asegurar que cualquier archivo que se ingrese a la base de datos (no solo PDFs) tenga su hash para identificación única.
*   `[ ]` **Extracción de Datos de Diferentes Dominios:** Implementar la lógica para extraer información de los distintos dominios web donde se publican las cartolas.
*   `[ ]` **Renombrar Archivos Procesados:** Implementar un sistema para renombrar los archivos PDF/XLS procesados con un formato estandarizado (ej. `[TipoDocumento]_[Cuenta]_[Fecha]_[HashCorto].pdf`).
*   `[ ]` **Revisar y Validar Esquema de BD:** Confirmar que el esquema actual (`create_new_tables.sql`) es adecuado para el escalamiento y las necesidades futuras.
*   `[ ]` **Implementar Ingesta Robusta de XLS:** Re-evaluar o mejorar el mecanismo de parsing para archivos XLS de bancos.
*   `[ ]` **Procesamiento de Datos Bancarios:** Implementar la lógica para transformar los datos crudos de `bank_account_transactions_raw` y `credit_card_transactions_raw` a la tabla `transactions`.
*   `[ ]` **Manejo de Duplicados y Actualizaciones (Nivel Transacción):** Implementar lógica para identificar y manejar transacciones individuales duplicadas.
*   `[ ]` **Optimización de Consultas:** Revisar y optimizar las consultas SQL para asegurar un rendimiento eficiente.
*   `[ ]` **Estrategia de Backup y Recuperación:** Definir e implementar una estrategia de backup y recuperación para la base de datos.

### Fase 3: Sistema Genérico de Ingesta de Documentos (Planificada)
*   `[ ]` **Implementar Sistema Genérico de Ingesta:** Desarrollar un sistema capaz de procesar cualquier tipo de PDF o documento estructurado, inferir su esquema y mapearlo a la base de datos de forma flexible.
