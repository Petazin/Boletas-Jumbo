# Historial de Cambios

## 2025-09-01
- **feat(ingestion)**: Implementa la ingesta de cartolas de Línea de Crédito de Banco Falabella.
    - Se creó el script `ingest_xls_falabella_linea_credito.py` y la tabla `transacciones_linea_credito_raw` para manejar este nuevo producto.
    - Se crearon scripts de utilidad (`setup_linea_credito_table.py`, `reset_database.py`) para mejorar la gestión del esquema de la BD.
- **fix(ingestion)**: Corrige error de inserción de valores `NaN` en múltiples scripts.
    - Se modificaron los scripts `ingest_xls_national_cc.py` y `ingest_xls_falabella_cuenta_corriente.py` para convertir valores `NaN` de pandas a `None` antes de la inserción, solucionando el error `Unknown column 'nan'`.
- **fix(pdf-parser)**: Mejora la robustez del parseo de números en cartolas PDF.
    - Se ajustó la función de limpieza en `ingest_pdf_bank_statement.py` para manejar casos donde el extractor de texto une columnas adyacentes, evitando errores de conversión a `float`.
- **chore(testing)**: Realiza prueba de ingesta completa de extremo a extremo.
    - Se validó el funcionamiento de todos los scripts de ingesta (`boletas`, `pdf`, `xls`) contra una base de datos limpia, corrigiendo múltiples errores y asegurando la robustez del sistema.
- **docs(roadmap)**: Añade nuevas tareas de arquitectura al roadmap.
    - Se incluyeron mejoras para el manejo transaccional de la ingesta y la reubicación inteligente de archivos procesados.

## 2025-08-29
- **fix(categorization)**: Corrige clasificación de yogures por orden de reglas.
    - Se reordena la lógica en `product_categorizer.py` para que la categoría "Lácteos y Huevos" se verifique antes que "Productos de Limpieza", solucionando la clasificación incorrecta de yogures en bolsa.
- **feat(ingestion)**: Implementa la ingesta de cartolas de Banco Falabella.
    - Se creó el script `ingest_xls_falabella_cc.py` para procesar archivos XLS de tarjetas de crédito de Banco Falabella.
    - El script identifica dinámicamente la cabecera de transacciones y mapea las columnas específicas del formato.
    - Se añadió la librería `openpyxl` a `requirements.txt` como nueva dependencia para el manejo de archivos `.xlsx`.

## 2025-08-28
- **feat(ingestion)**: Implementa ingesta robusta de cartolas bancarias y mejora procesamiento de boletas.
    - Se actualiza el esquema de la base de datos para soportar nuevos tipos de documentos y metadatos.
    - Se mejora la ingesta de cartolas PDF y XLS (nacionales e internacionales) con el uso de `document_type` y el movimiento de archivos procesados.
    - Se optimiza el procesamiento de boletas mediante `multiprocessing` para un procesamiento paralelo de PDFs.
    - Se añade `archivos_procesados/` al `.gitignore`.

## 2025-08-27
- **refactor(files)**: Mejora la estructura de carpetas para estados de cuenta bancarios.
    - Se añadió `PROCESSED_BANK_STATEMENTS_DIR` en `config.py` para definir la ubicación de los archivos bancarios procesados.
    - Se modificaron los scripts `ingest_pdf_bank_statement.py`, `ingest_xls_national_cc.py` e `ingest_xls_international_cc.py` para mover los archivos procesados a este nuevo directorio, manteniendo la sub-estructura original.
    - Esto formaliza el estado "procesado" de los archivos bancarios, dejando los directorios de descarga solo con archivos pendientes de procesar.

## 2025-08-27
- **feat(ingestion)**: Implementa mecanismo de hashing para boletas de Jumbo.
    - Se añadió una columna `file_hash` a la tabla `historial_descargas` para almacenar el hash SHA-256 de los archivos de boletas.
    - Se modificó `download_boletas.py` para calcular el hash de cada boleta descargada y guardarlo en la base de datos.
    - Se actualizó `process_boletas.py` para utilizar el `file_hash` como mecanismo principal para evitar el reprocesamiento de boletas duplicadas.

## 2025-08-27
- **refactor(db)**: Traduce completamente el esquema de la base de datos al español.
    - Se han renombrado todas las tablas y columnas de la base de datos para que utilicen nombres en español, mejorando la legibilidad y mantenibilidad del proyecto.
    - Se han actualizado todos los scripts que interactúan con la base de datos para que utilicen los nuevos nombres de tablas y columnas.
    - Se ha centralizado la creación de todas las tablas en el archivo `create_new_tables.sql`.
- **docs(readme, changelog)**: Actualiza la documentación para reflejar la traducción de la base de datos.

## 2025-08-27
- **fix(ingestion)**: Corrige errores de columna y sintaxis en scripts de ingesta de cartolas.
    - Se solucionó `SyntaxError` en `ingest_xls_international_cc.py`.
    - Se corrigieron errores de `Unknown column 'file_path'` en `ingest_pdf_bank_statement.py`, `ingest_xls_national_cc.py` e `ingest_xls_international_cc.py` al actualizar las funciones `insert_metadata` para usar `original_filename` y `document_type`.
    - Se resolvió el error `Unknown column 'status'` en `alter_table.py` ajustando la sentencia `ALTER TABLE`.
    - Se actualizó `GEMINI.md` y `README.md` para reflejar el estado actual del proyecto y los módulos.
    - Se confirmó la funcionalidad completa del pipeline de ingesta de datos de extremo a extremo.

## 2025-08-26
- **feat(ingestion)**: Implementa un sistema robusto de ingesta de cartolas bancarias en formato PDF.
    - Se creó el script `ingest_pdf_bank_statement.py` para procesar múltiples archivos PDF de cartolas del Banco de Chile.
    - La extracción de datos se realiza mediante un parseo manual basado en coordenadas, resistente a errores de formato del PDF.
    - Se implementó un sistema de detección de duplicados basado en el hash (SHA-256) del contenido del archivo, evitando la re-ingesta de datos.
    - El sistema ahora puede procesar un directorio completo de archivos PDF, omitiendo los que ya han sido registrados en la base de datos.
- **feat(ingestion)**: Implementa ingesta robusta de cartolas de tarjeta de crédito en formato XLS.
    - Se creó el script `ingest_xls_bank_statement.py` para procesar múltiples archivos XLS de cartolas de tarjeta de crédito.
    - Se implementó la detección dinámica de la fila de cabecera de transacciones.
    - Se añadió el cálculo de `original_charge_date` y `installment_charge_date` a partir de la columna 'Cuotas'.
    - Se aseguró la creación de la tabla `credit_card_transactions_raw` con el esquema adecuado.
- **refactor(db)**: Reestructura la tabla de metadatos (`bank_statement_metadata_raw`) para añadir la columna `file_hash` con un índice `UNIQUE`, asegurando la integridad de los datos.
- **chore(cleanup)**: Elimina scripts de un solo uso (`alter_table.py`, `verify_bank_data.py`).

## 2025-08-25
- **docs(roadmap)**: Actualiza `GEMINI.md` con un roadmap detallado para el diseño de bases de datos escalables.
- **feat(ingestion)**: Implementa la ingesta de extractos bancarios XLS y mejora la robustez del código.
    - Se creó `ingest_bank_statements.py` para automatizar la búsqueda y procesamiento de archivos XLS de bancos.
    - Se corrigió la duplicación de código en `bank_ingestion.py`.

## 2025-08-25
- **docs(changelog)**: Actualiza CHANGELOG y README con mejoras de calidad (1682bc8)
- **refactor(code-quality)**: Mejora la calidad del código y el formato (bbb3e4c)
- **docs(roadmap)**: Actualiza estado de tareas completadas (b526b7b)
- **feat(tests)**: Completa pruebas unitarias para pdf_parser (b697762)
- **Docs**: Actualizar directrices de Gemini con entorno y estrategia de depuración (c90daff)
- **Chore**: Añadir `__init__.py` a la carpeta de tests

Se añadió un archivo `__init__.py` vacío a la carpeta `tests` para asegurar que `pytest` descubra correctamente los módulos de prueba y `conftest.py`. (4456b43)
- **Feat**: Añadir y corregir pruebas unitarias para `pdf_parser.py`

- Se añadió una prueba unitaria para la función `parse_chilean_number`.
- Se corrigió el orden de los parámetros de los mocks en las pruebas existentes.
- Se ajustó la expresión regular `CANTIDAD_PRECIO` en `config.py` para manejar espacios en blanco iniciales, resolviendo un error de aserción en `test_process_pdf_success`.n- Se configuró `conftest.py` para asegurar la correcta importación de módulos en el entorno de pruebas. (5485913)
- **Docs**: Actualizar estado del roadmap en GEMINI.md (1979088)
- **Mejora**: Formato de mensajes de log en `download_boletas.py`

Se ajustó el formato de los mensajes de log en `download_boletas.py` para mejorar la legibilidad, dividiendo líneas largas en varias más cortas. (d58ac74)
- **feat**: Actualización de progreso y corrección de linting (77078f4)
- **feat**: Corregir error E402 en tests/test_pdf_parser.py (0679968)

## 2025-08-24
- **feat**: Implementar cuarentena de PDFs y sanity checks (576c7f4)
- **feat**: Centralizar patrones regex en config.py (fbed0a7)
- **feat**: Actualización general y adición de pruebas iniciales (4021c1b)

## 2025-08-23
- **Docs**: Creación de CHANGELOG.md (9e20152)
- **Mejora**: Escalabilidad en Descarga y Procesamiento de Archivos (1886887)

## 2025-08-22
- **chore**: Actualizar gitignore y dejar de rastrear archivos (a101db2)

## 2025-08-18
- **feat(download)**: Mejorar login y actualizar gitignore (2218013)
- **chore(git)**: Dejar de rastrear archivos de registro (571481b)
- **feat(categorizacion)**: Refinar clasificación de productos con nuevas palabras clave (e947201)
- **feat(categorizacion)**: Mejorar y ampliar la lógica de categorización de productos (4cf944f)

## 2025-08-17
- **Feat**: Mejorar categorización de productos y limpieza de archivos temporales (98825a8)
- **Feat**: Extraer y almacenar hora de boleta (7983a3b)
- **Fix**: Usar auth_plugin para compatibilidad con mysql-connector-python (e35fa4c)
- **Fix**: Añadir allow_public_key_retrieval para compatibilidad con MySQL 8+ (f673d0f)
- **Docs**: Update README and add comments to all scripts (0a6df77)
- **Refactor**: Move PDF parsing logic to its own module (e84b225)
- **Refactor**: Move product categorization to its own module (e1cf0c0)
- **Refactor**: Create database_utils module (13ec14d)
- **Refactor**: Centralize configuration into config.py (1bc525b)
- **Add**: requirements.txt (090b8d0)
- **Add**: .gitignore (79c887a)
- **Initial**: commit (5ac646a)