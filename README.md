# Proyecto de Finanzas Personales

## Visión General del Proyecto

El objetivo final de este proyecto es construir una aplicación integral para la gestión de finanzas personales. Esta aplicación permitirá a los usuarios tener un control total sobre sus ingresos y gastos de forma automatizada, conectándose a diversas fuentes (bancos, tiendas), procesando la información, categorizándola inteligentemente y presentándola en un dashboard interactivo con alertas y presupuestos.

El desarrollo se ha dividido en dos fases principales:

1.  **Fase 1 (Completada):** Perfeccionar un motor de análisis de boletas de supermercado (Jumbo) para extraer y analizar datos de consumo de forma automatizada. Esta fase se centró en construir y optimizar la base de extracción y estructuración de datos.
2.  **Fase 2 (Planificada):** Expandir la aplicación para que sea un gestor financiero completo, capaz de procesar cualquier tipo de boleta o cartola, controlar gastos e ingresos, y ayudar a mantener un presupuesto mensual saludable.

---

## Fase 1: Analizador de Boletas de Supermercado (Jumbo) - Completada

### Descripción General

La Fase 1 de este proyecto se ha completado con éxito. Se ha desarrollado un motor robusto y eficiente para la extracción y análisis automatizado de datos de boletas de supermercado Jumbo. Este motor es capaz de descargar boletas en formato PDF, parsear su contenido para extraer información estructurada de productos y transacciones, y almacenar estos datos en una base de datos MySQL para su posterior análisis. La fase incluyó mejoras significativas en la robustez, mantenibilidad y rendimiento del sistema.

### Requisitos Previos

Para ejecutar este proyecto, necesitarás lo siguiente:

*   **Python 3.x:** Se recomienda utilizar la última versión estable de Python 3.
*   **Git:** Para clonar el repositorio.
*   **Un servidor de base de datos MySQL:** Asegúrate de que esté instalado y en funcionamiento.
*   **Google Chrome:** Necesario para la descarga automatizada de boletas a través de Selenium.

### Instalación y Configuración

Sigue estos pasos para configurar el proyecto en tu entorno local:

1.  **Clonar el Repositorio:**
    Abre tu terminal o línea de comandos y ejecuta:
    ```bash
    git clone https://github.com/Petazin/Boletas-Jumbo.git
    cd Boletas-Jumbo
    ```

2.  **Crear y Activar un Entorno Virtual (Recomendado):**
    Es una buena práctica aislar las dependencias del proyecto.
    ```bash
    python -m venv venv
    # En Windows:
    .\venv\Scripts\activate
    # En macOS/Linux:
    source venv/bin/activate
    ```

3.  **Instalar Dependencias:**
    Con el entorno virtual activado, instala todas las librerías necesarias:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar la Base de Datos:**
    *   Asegúrate de que tu servidor MySQL esté en funcionamiento.
    *   Crea una base de datos. El nombre por defecto esperado por la aplicación es `Boletas`. Puedes crearla con un cliente MySQL o desde la línea de comandos:
        ```sql
        CREATE DATABASE Boletas;
        ```
    *   **Configura las credenciales de la base de datos:** Abre el archivo `config.py` y edita el diccionario `DB_CONFIG` con tu `host`, `user`, `password` y `database` si son diferentes a los valores por defecto.
    *   **Configura las rutas de archivos:** En `config.py`, ajusta `DOWNLOAD_PATH`, `QUARANTINE_PATH` y `PROCESS_LOG_FILE` según tus preferencias.

### Estructura del Proyecto y Arquitectura

El proyecto sigue una arquitectura modular, donde cada archivo tiene una responsabilidad única, facilitando la mantenibilidad y escalabilidad:

*   **`config.py`**: **Módulo central de configuración.** Contiene todas las constantes, credenciales de la base de datos, rutas a directorios, URLs importantes y expresiones regulares (regex) utilizadas en el parsing. Es la única ubicación donde deberías necesitar realizar cambios de configuración.
*   **`database_utils.py`**: **Utilidad para la base de datos.** Encapsula la lógica de conexión y desconexión a la base de datos MySQL, asegurando una gestión segura y centralizada de las conexiones.
*   **`product_categorizer.py`**: **Módulo de lógica de negocio.** Contiene la función `categorize_product` que asigna una categoría predefinida a cada producto basándose en palabras clave y reglas específicas.
*   **`pdf_parser.py`**: **Módulo de extracción y parsing.** Su responsabilidad principal es leer un archivo PDF, extraer su texto y parsearlo utilizando expresiones regulares para obtener datos estructurados de la boleta (ID de boleta, fecha, hora y una lista detallada de productos).
*   **`download_boletas.py`**: **Script de automatización de descarga.** Orquesta el proceso de descarga de boletas en formato PDF desde el sitio web de Jumbo utilizando Selenium. Gestiona el inicio de sesión y la navegación para obtener los archivos.
*   **`process_boletas.py`**: **Script orquestador de procesamiento.** Coordina el flujo de trabajo principal: lee los PDFs descargados, utiliza `pdf_parser.py` para extraer los datos, y `database_utils.py` para insertar o actualizar la información de los productos en la base de datos. Incorpora `multiprocessing` para un procesamiento eficiente en paralelo.
*   **`export_data.py`**: **Script de exportación.** Se conecta a la base de datos (a través de `database_utils.py`) y exporta la tabla `boletas_data` a un archivo CSV (`boletas_data.csv`) para análisis externo o integración con otras herramientas.
*   **`get_otros_productos.py`**: **Script auxiliar.** Diseñado para extraer información adicional de productos que no son directamente parte de la boleta principal, como productos de ofertas o promociones especiales. (Si aplica, detallar su integración).
*   **`cuarentena_pdfs/`**: **Directorio de cuarentena.** Los PDFs que no pueden ser procesados correctamente por `pdf_parser.py` son movidos a esta carpeta para una revisión manual, evitando que detengan el flujo de procesamiento principal.
*   **`descargas/Jumbo/`**: **Directorio de descarga.** Aquí se guardan los PDFs de las boletas descargadas exitosamente.
*   **`tests/`**: **Directorio de pruebas unitarias.** Contiene las pruebas automatizadas desarrolladas con `pytest` para asegurar la funcionalidad y robustez de los componentes críticos del proyecto, especialmente `pdf_parser.py`.

### Esquema de la Base de Datos (`boletas_data`)

La tabla `boletas_data` almacena la información detallada de cada producto de las boletas procesadas. Su esquema es el siguiente:

```sql
CREATE TABLE IF NOT EXISTS boletas_data (
    boleta_id VARCHAR(255),             -- Identificador único de la boleta
    filename VARCHAR(255),              -- Nombre del archivo PDF de la boleta
    Fecha DATE,                         -- Fecha de la compra
    Hora TIME,                          -- Hora de la compra
    codigo_SKU VARCHAR(255),            -- Código SKU del producto
    Cantidad_unidades INT,              -- Cantidad de unidades compradas
    Valor_Unitario DECIMAL(15, 2),      -- Precio unitario del producto
    Cantidad_comprada_X_Valor_Unitario VARCHAR(255), -- Cantidad comprada por valor unitario (puede ser una cadena si incluye texto)
    Descripcion_producto TEXT,          -- Descripción completa del producto
    Total_a_pagar_producto DECIMAL(15, 2), -- Total pagado por este producto (después de descuentos)
    Descripcion_Oferta TEXT,            -- Descripción de la oferta aplicada al producto
    Cantidad_reducida_del_total DECIMAL(15, 2), -- Cantidad reducida del total debido a ofertas
    Categoria VARCHAR(255),             -- Categoría asignada al producto
    PRIMARY KEY (boleta_id, codigo_SKU) -- Clave primaria compuesta para evitar duplicados
);
```

### Uso Detallado y Flujo de Trabajo

El proceso de extracción y almacenamiento de datos de boletas sigue un flujo de trabajo secuencial de tres pasos. Asegúrate de ejecutar cada script en el orden indicado:

1.  **Descargar las Boletas (`download_boletas.py`):**
    Este script automatiza la descarga de tus boletas desde el sitio web de Jumbo.
    ```bash
    python download_boletas.py
    ```
    *   **Proceso:** Al ejecutarlo, se abrirá una ventana de Google Chrome controlada por Selenium. Deberás iniciar sesión manualmente en Jumbo.cl con tus credenciales. Una vez que hayas iniciado sesión y la página principal esté cargada, regresa a la terminal y presiona `Enter` para que el script continúe con la descarga automática de las boletas disponibles.
    *   **Registro:** Las boletas descargadas se registran en la tabla `download_history` de la base de datos con un estado `Downloaded`. Esto permite al sistema saber qué archivos deben ser procesados.

2.  **Procesar y Guardar en Base de Datos (`process_boletas.py`):**
    Este script lee los PDFs descargados, extrae la información y la guarda en tu base de datos MySQL.
    ```bash
    python process_boletas.py
    ```
    *   **Proceso:** El script identifica los archivos PDF con estado `Downloaded` en la base de datos. Utiliza `multiprocessing` para procesar múltiples PDFs en paralelo, lo que acelera significativamente la ingesta de grandes volúmenes de boletas. Cada PDF es parseado para extraer detalles de la boleta y de cada producto.
    *   **Manejo de Errores:** Si un PDF no puede ser procesado correctamente (ej. archivo corrupto, formato inesperado), el archivo se moverá automáticamente al directorio `cuarentena_pdfs/` para una revisión manual. El estado en la base de datos se actualizará a `Error - Parsing failed` o `Error - File not found`.
    *   **Actualizaciones:** Si se intenta insertar un producto que ya existe (identificado por `boleta_id` y `codigo_SKU`), la base de datos actualizará automáticamente los campos relevantes (`Cantidad_unidades`, `Valor_Unitario`, etc.) gracias a la cláusula `ON DUPLICATE KEY UPDATE`.

3.  **Exportar a CSV (Opcional) (`export_data.py`):**
    Si necesitas los datos en un formato de archivo plano para análisis externo o para usar con otras herramientas, este script generará un archivo CSV.
    ```bash
    python export_data.py
    ```
    *   **Salida:** Este script se conectará a tu base de datos y exportará todo el contenido de la tabla `boletas_data` a un archivo llamado `boletas_data.csv` en el directorio raíz del proyecto.

### Mejoras Implementadas en Fase 1

La Fase 1 ha sido sometida a un proceso de mejora continua para aumentar su robustez, mantenibilidad y rendimiento. Las siguientes tareas clave han sido completadas:

*   **Centralización de Configuración:** Todas las constantes, credenciales, rutas y expresiones regulares se han consolidado en `config.py`, facilitando la gestión y modificación del proyecto.
*   **Mejora de Validación y Manejo de Errores:** Se implementó un sistema de "cuarentena" para PDFs que fallan en el procesamiento, y se añadieron "sanity checks" para validar la coherencia de los datos extraídos.
*   **Creación de Pruebas Unitarias:** Se desarrolló un conjunto exhaustivo de pruebas automatizadas utilizando `pytest` para `pdf_parser.py` y otros componentes críticos, asegurando la fiabilidad del código.
*   **Optimización de Rendimiento:** Se aplicó `multiprocessing` en `process_boletas.py` para paralelizar el procesamiento de boletas, mejorando significativamente la velocidad de ingesta de datos.
*   **Correcciones de Formato y Espaciado:** Se realizaron ajustes para asegurar la consistencia del estilo de código y la legibilidad.
*   **Correcciones de Importación:** Se resolvieron problemas de importaciones no ubicadas al inicio de los archivos (`E402`).
*   **Revisión de Variables No Utilizadas:** Se eliminaron variables locales no utilizadas (`F841`) para limpiar el código.
*   **Completar Pruebas Unitarias para `pdf_parser.py`:** Se implementó un mocking avanzado de `pypdf.PdfReader` para asegurar una cobertura completa y fiable de las pruebas del parser de PDFs.

---

## Fase 2: Gestor Integral de Finanzas Personales - Planificada

La Fase 2 del proyecto se centrará en expandir la aplicación a un gestor financiero completo. El objetivo es crear una herramienta que permita analizar cualquier tipo de boleta o cartola, categorizar tanto gastos como ingresos, y proporcionar un control detallado del presupuesto mensual.

El roadmap detallado para la Fase 2, incluyendo el diseño de una base de datos escalable, soporte multi-origen, manejo de ingresos, categorización jerárquica, dashboards financieros y un sistema de alertas, se encuentra documentado en el archivo `GEMINI.md` del proyecto.

## Fase 2: Gestor Integral de Finanzas Personales - Planificada

La Fase 2 del proyecto se centrará en expandir la aplicación a un gestor financiero completo. El objetivo es crear una herramienta que permita analizar cualquier tipo de boleta o cartola, categorizar tanto gastos como ingresos, y proporcionar un control detallado del presupuesto mensual.

El roadmap detallado para la Fase 2 incluye:

*   `[ ]` **Diseño de Base de Datos Escalable (¡Nuevo!):** Modificar la estructura de la base de datos para soportar múltiples orígenes de datos (bancos, tiendas), tipos de transacciones (ingresos/egresos) y la nueva categorización jerárquica.
*   `[ ]` **Soporte Multi-Origen:** Añadir la capacidad de procesar boletas y cartolas de bancos, otras tiendas, tarjetas de crédito, etc.
*   `[ ]` **Manejo de Ingresos (¡Nuevo!):** Implementar la lógica para identificar y registrar transacciones de ingresos.
*   `[ ]` **Categorización Jerárquica:** Implementar un sistema de dos niveles: Categorías principales (ej. "Vivienda", "Transporte", "Alimentación") y sub-categorías (ej. "Supermercado", "Restaurantes", "Metro").
*   `[ ]` **Organización de Archivos:** Clasificar los archivos PDF/CSV descargados en carpetas según su origen.
*   `[ ]` **Dashboard Financiero (¡Nuevo!):** Crear un panel principal que muestre el balance mensual (ingresos vs. gastos), gráficos por categoría y alertas.
*   `[ ]` **Sistema de Alertas y Presupuestos:** Crear notificaciones para gastos no categorizados, consumos que superen un límite predefinido, etc.
*   `[ ]` **Interfaz Gráfica (GUI) Unificada:** Evolucionar la GUI de la Fase 1 para que soporte todas las nuevas funcionalidades (múltiples orígenes, ingresos, dashboard, etc.).
