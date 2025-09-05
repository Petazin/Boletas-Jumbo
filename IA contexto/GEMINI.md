## 2. Configuración Específica del Proyecto

### 2.1. Visión General y Estado Actual

*   **Visión Final del Producto:**
    > El objetivo es crear una aplicación integral de finanzas personales que permita al usuario tener un control total sobre sus ingresos y gastos de forma automática. El sistema deberá ser capaz de conectarse a distintas fuentes (bancos, tiendas), procesar la información, categorizarla inteligentemente y presentarla en un dashboard interactivo con alertas y presupuestos.

*   **Fases de Desarrollo:**
    *   **Fase 1 (Completada):** Crear y validar el motor de análisis de documentos con un caso de uso específico: el procesamiento de boletas de supermercado Jumbo.
    *   **Fase 2 (En Progreso):** Expandir la aplicación para convertirla en un gestor financiero completo. Esto incluye soportar múltiples tipos de documentos (cartolas bancarias, otras boletas), manejar ingresos, implementar un sistema de categorías jerárquico y construir una interfaz de usuario con dashboards y alertas.
    *   **Fase 3 (Planificada):** Implementar un sistema genérico de ingesta de documentos, capaz de procesar cualquier tipo de PDF o documento estructurado, inferir su esquema y mapearlo a la base de datos.

*   **Estado Actual:**
    > La Fase 1 es funcional. La Fase 2 ha avanzado significativamente con la implementación de la **capa de staging de datos** (descrita en la sección 2.2). Todos los scripts de ingesta ahora cargan los datos crudos en tablas de staging dedicadas, sentando una base robusta para el procesamiento posterior. Los siguientes pasos son validar la ingesta de todos los tipos de documentos y luego construir el proceso de transformación y traspaso de datos desde staging a las tablas `raw`.

### 2.2. Capa de Staging de Datos

Esta sección define la arquitectura y los principios para la capa de staging de datos, crucial para asegurar la visibilidad y la integridad de los datos extraídos antes de su procesamiento final.

*   **Extracción Dedicada:** La información de cada cartola o documento será extraída y almacenada en una tabla de staging específica.
*   **Nomenclatura Clara:** El nombre de cada tabla de staging debe reflejar claramente el tipo de dato y su origen. Por ejemplo: `cuenta_corriente_banco_chile_staging`, `tarjeta_credito_falabella_nacional_staging`. No se permitirán tablas de extracción genéricas.
*   **Scripts de Extracción Específicos:** Cada proceso de extracción que alimente una tabla de staging tendrá un archivo `.py` dedicado, cuyo nombre estará relacionado con la tabla de destino y los datos que se ingresan.
*   **Validaciones Robustas:**
    *   **Por Línea:** Se implementarán validaciones para evitar la duplicación de registros individuales al momento de la inserción en la tabla de staging.
    *   **Por Archivo:** Se realizarán validaciones a nivel de archivo, incluyendo la verificación de sumas de totales y el recuento de registros, para asegurar la integridad y completitud de los datos ingresados.
*   **Alimentación de Tablas Raw:** Estas tablas de staging servirán como la fuente de datos "limpia" y verificada para las tablas raw finales del sistema. Esto permitirá consolidar datos de distintos orígenes en una única tabla raw por tipo de dato (ej. `linea_credito_raw` consolidará todas las transacciones de línea de crédito de diferentes bancos).
*   **Metadatos Completos:** Toda carga de datos a las tablas de staging incluirá metadatos relevantes si están disponibles en el documento original, asegurando la trazabilidad y el contexto de la información.

### 2.3. Reglas y Preferencias del Proyecto

*   **Idioma Preferido:**
    > Español, tanto para la comunicación como para los mensajes de commit de Git.

*   **Entorno de Desarrollo:**
    > El proyecto está programado y optimizado para ejecutarse en un entorno Windows.

*   **Gestor de Paquetes y Dependencias:**
    > Usar `pip` y el archivo `requirements.txt`. No se deben añadir nuevas librerías sin una justificación clara.

*   **Estilo de Código y Linters:**
    > Seguir el estilo estándar de Python (PEP 8). No hay un linter configurado formalmente aún.

*   **Frameworks y Librerías Clave:**
    > `Selenium` para la descarga de boletas, `pdfplumber` para la lectura de PDFs, `pandas` para la manipulación de datos, y `mysql-connector-python` para la base de datos.

*   **Preferencias de Commits:**
    > Los mensajes deben ser en español y explicar el 'porqué' del cambio, no solo el 'qué'.

### 2.4. Roadmap Activo y Tareas Prioritarias

#### Fase 1: Mejoras del Motor de Boletas (Completado)
*   `[x]` **Centralizar Configuración:** Mover regex y constantes a `config.py`.
*   `[x]` **Mejorar Validación y Errores:** Implementar cuarentena de PDFs y `sanity checks`.
*   `[x]` **Crear Pruebas Unitarias:** Desarrollar pruebas con `pytest`.
*   `[x]` **Optimizar Rendimiento:** Aplicar `multiprocessing` para el procesamiento de boletas.
*   `[x]` **Corregir errores de formato y espaciado.**
*   `[x]` **Corregir errores de importación (`E402`).**
*   `[x]` **Revisar variables locales no utilizadas (`F841`).**
*   `[x]` **Completar pruebas unitarias para `pdf_parser.py`.**

#### Fase 2: Gestor Financiero Integral (En Progreso)
*   `[x]` **Implementar Ingesta Robusta de Cartolas PDF:** Desarrollar un mecanismo de parsing configurable para archivos PDF de bancos, con detección de duplicados por contenido (hash), utilizando el campo `document_type` y moviendo los archivos procesados.
*   `[x]` **Expandir Ingesta de Cartolas (PDF/XLS):** Implementada la ingesta de cartolas de tarjeta de crédito nacional e internacional (XLS), con soporte para `document_type` y movimiento de archivos procesados.
*   `[x]` **Aplicar Hashing a Todos los Archivos Analizados:** Asegurado que cualquier archivo que se ingrese a la base de datos (no solo PDFs) tenga su hash para identificación única, con soporte para `document_type` y movimiento de archivos procesados.
*   `[x]` **Implementar Sistema de Abonos/Cargos:** Crear y utilizar la tabla 'abonos_mapping' para diferenciar pagos en tarjetas de crédito.
*   `[x]` **Implementar Ingestión Robusta de XLS para Banco Falabella:** Desarrollar un mecanismo de parsing específico para los archivos XLS de tarjetas de crédito de Banco Falabella.
*   `[x]` **Expandir Ingesta de Banco Falabella:** Añadir soporte para Cuenta Corriente y Línea de Crédito.
*   `[x]` **Revisar y Validar Esquema de BD:** Confirmado que el esquema actual (`create_new_tables.sql`) es adecuado para el escalamiento y las necesidades futuras, y se han realizado ajustes en `alter_table.py` para su compatibilidad.
*   `[x]` **Implementar capa de staging para datos extraídos de archivos:** Crear tablas por tipo de documento/origen con la estructura original de los datos extraídos, antes de cualquier manipulación o transformación. (Esta tarea ahora se detalla en la sección 2.2)
*   `[ ]` **Implementar Validación Post-Ingesta en Staging:** Añadir validación de conteo de registros y suma de montos para todos los scripts de ingesta.
    *   `[x]` Implementado en `ingest_xls_national_cc.py`.
*   `[ ]` **Renombrar Archivos Procesados:** Implementar un sistema para renombrar los archivos PDF/XLS procesados con un formato estandarizado (ej. `[TipoDocumento]_[Cuenta]_[Fecha]_[HashCorto].pdf`).
*   `[ ]` **Clasificación de Transacciones Bancarias:** Diseñar e implementar un sistema de clasificación para las transacciones bancarias (cuenta corriente y tarjetas), similar al categorizador de productos. Debe utilizar una tabla de mapeo en la BD para asignar categorías basadas en la descripción de las transacciones.
*   `[ ]` **Procesamiento de Datos Bancarios:** Implementar la lógica para transformar los datos crudos de las tablas de staging a las tablas raw consolidadas, y posteriormente a la tabla `transactions` para análisis final.
*   `[ ]` **Desarrollar Interfaz de Usuario:** Construir un dashboard interactivo para la visualización de datos, alertas y presupuestos.
*   `[ ]` **Manejo de Duplicados y Actualizaciones (Nivel Transacción):** Implementar lógica para identificar y manejar transacciones individuales duplicadas.
*   `[ ]` **Optimización de Consultas:** Revisar y optimizar las consultas SQL para asegurar un rendimiento eficiente.
*   `[ ]` **Estrategia de Backup y Recuperación:** Definir e implementar una estrategia de backup y recuperación para la base de datos.

#### Fase 2.1: Mejoras de Arquitectura y Robustez del Proceso de Ingesta
*   `[x]` **Manejo Transaccional de la Ingesta:** Modificar todos los scripts para que el `hash` de un archivo se guarde en la base de datos únicamente si el archivo y **todas** sus transacciones han sido procesadas e insertadas con éxito. Esto evitará registros "huérfanos" que impiden el reprocesamiento.
*   `[x]` **Reubicación Inteligente de Archivos:** Mejorar la lógica de movimiento de archivos para que al pasar un documento a la carpeta `procesados/` dentro de su directorio de origen, se conserve su estructura de carpetas original. Esto facilitará los ciclos de prueba y la re-ingesta manual de datos, y se complementa con un logging centralizado de movimientos de archivos.

#### Fase 2.2: Refactorización del Esquema Raw (Pendiente)
*   `[ ]` **Implementar Flujo Staging->Raw para Línea de Crédito PDF:** Añadir la lógica para transferir los datos desde `staging_linea_credito_banco_chile_pdf` a `raw_transacciones_linea_credito`.
*   `[ ]` **Renombrar Tabla Raw de Cuenta Corriente:** Cambiar `raw_transacciones_cuenta_bancaria` por `raw_transacciones_cta_corriente` y actualizar todos los scripts dependientes.
*   `[ ]` **Dividir Tabla Raw de Tarjeta de Crédito:** Reemplazar `raw_transacciones_tarjeta_credito` por `raw_transacciones_tarjeta_credito_nacional` y `raw_transacciones_tarjeta_credito_internacional`, y actualizar los scripts de ingesta correspondientes.

#### Fase 3: Sistema Genérico de Ingesta de Documentos (Planificada)
*   `[ ]` **Extracción de Datos de Diferentes Dominios:** Implementar la lógica para extraer información de los distintos dominios web donde se publican las cartolas.
*   `[ ]` **Implementar Sistema Genérico de Ingesta:** Desarrollar un sistema capaz de procesar cualquier tipo de PDF o documento estructurado, inferir su esquema y mapearlo a la base de datos de forma flexible.
*   `[ ]` **Implementar Ingestión Robusta de XLS:** Re-evaluar o mejorar el mecanismo de parsing para archivos XLS de bancos.