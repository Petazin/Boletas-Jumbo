# Proyecto de Finanzas Personales

## Visión del Proyecto

El objetivo final es construir una aplicación integral para la gestión de finanzas personales. El desarrollo se dividirá en dos fases principales:

1.  **Fase 1:** Perfeccionar un analizador de boletas de supermercado (Jumbo) para extraer y analizar datos de consumo.
2.  **Fase 2:** Expandir la aplicación para que sea un gestor financiero completo, capaz de procesar cualquier tipo de boleta o cartola, controlar gastos e ingresos, y ayudar a mantener un presupuesto mensual saludable.

---

## Fase 1: Analizador de Boletas de Supermercado (Jumbo)

### Requisitos Previos

*   Python 3.x
*   Git
*   Un servidor de base de datos MySQL

### Instalación y Configuración

1.  **Clonar el Repositorio:**
    ```bash
    git clone https://github.com/Petazin/Boletas-Jumbo.git
    cd Boletas-Jumbo
    ```

2.  **Instalar Dependencias:**
    Se recomienda crear un entorno virtual primero. Luego, instalar todas las librerías necesarias con el siguiente comando:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurar la Base de Datos:**
    *   Asegúrate de que tu servidor MySQL esté en funcionamiento.
    *   Crea una base de datos. El nombre por defecto es `Boletas`.
    *   Abre el archivo `config.py` y edita el diccionario `DB_CONFIG` con tu `host`, `user`, `password` y `database` si son diferentes a los valores por defecto.

### Estructura del Proyecto

El proyecto ha sido refactorizado para tener una arquitectura modular, donde cada archivo tiene una responsabilidad única:

*   **`config.py`**: Módulo central de configuración. Contiene las credenciales de la base de datos, las rutas a directorios y archivos de log, y URLs importantes. **Es el único archivo que deberías necesitar modificar para la configuración.**

*   **`database_utils.py`**: Utilidad para la base de datos. Gestiona la conexión y desconexión de la base de datos de forma segura y centralizada.

*   **`product_categorizer.py`**: Módulo de lógica de negocio. Contiene la función `categorize_product` que asigna una categoría a cada producto basándose en palabras clave.

*   **`pdf_parser.py`**: Módulo de extracción. Su única responsabilidad es leer un archivo PDF, extraer el texto y parsearlo con expresiones regulares para devolver datos estructurados (ID de boleta, fecha y lista de productos).

*   **`download_boletas.py`**: Script orquestador. Inicia el proceso de descarga de boletas usando Selenium. Utiliza la configuración de `config.py`.

*   **`process_boletas.py`**: Script orquestador. Coordina el proceso de lectura de los PDFs. Llama a `pdf_parser.py` para extraer los datos y a `database_utils.py` para guardarlos en la base de datos.

*   **`export_data.py`**: Script orquestador. Se conecta a la base de datos (usando `database_utils.py`) y exporta la tabla `boletas_data` a un archivo CSV (`boletas_data.csv`).

### Uso

El flujo de trabajo se ejecuta en tres pasos, en el siguiente orden:

1.  **Descargar las Boletas:**
    ```bash
    python download_boletas.py
    ```
    *Se abrirá una ventana de Chrome. Deberás iniciar sesión manualmente en Jumbo.cl. Una vez hecho, presiona Enter en la terminal para continuar con la descarga automática.*

2.  **Procesar y Guardar en Base de Datos:**
    ```bash
    python process_boletas.py
    ```
    *Este script leerá todos los PDFs, los procesará y guardará los productos en tu base de datos MySQL.*

3.  **Exportar a CSV (Opcional):**
    ```bash
    python export_data.py
    ```
    *Si deseas tener los datos en un archivo plano, este script generará `boletas_data.csv`.*

### Roadmap de Mejoras (Fase 1)

Aunque la Fase 1 es funcional, se ha identificado un roadmap de mejoras para aumentar su robustez, mantenibilidad y rendimiento. La prioridad de implementación es la siguiente:

1.  `[ ]` **Crear Pruebas Unitarias:** Desarrollar un conjunto de pruebas automatizadas (con `pytest`) para `pdf_parser.py` y otros componentes críticos. Esto asegurará que los cambios futuros no rompan la funcionalidad existente.
    *   `[ ]` **Pendiente:** Resolver el mockeo avanzado de `pypdf.PdfReader` para las pruebas unitarias de `process_pdf`.
2.  `[ ]` **Calidad del Código:** Implementar herramientas como `pylint` o `flake8` para asegurar un estilo de codificación consistente y detectar posibles problemas en el código.
3.  `[ ]` **Centralizar Configuración:** Mover todas las expresiones regulares (regex), nombres de tablas y estados desde el código Python hacia el archivo `config.py` para facilitar futuras modificaciones.
4.  `[ ]` **Mejorar Validación y Manejo de Errores:**
    *   Implementar una "cuarentena" para los PDFs que fallen, moviéndolos a una carpeta separada para análisis manual.
    *   Añadir comprobaciones de coherencia en los datos extraídos (ej. `Cantidad * Precio ≈ Total`) para detectar errores de parsing.
5.  `[ ]` **Optimizar Rendimiento:** Investigar y aplicar procesamiento en paralelo (`multiprocessing`) en `process_boletas.py` para acelerar la ingesta de un gran volumen de boletas.
6.  `[ ]` **Documentación:** Ampliar el archivo `README.md` con instrucciones y ejemplos más detallados sobre el uso y la arquitectura del proyecto.

---

## Fase 2: Gestor Integral de Finanzas Personales

*   **Objetivo:** "Una aplicación que sirva para analizar cualquier boleta o cartola, categorizando los gastos inicialmente, pero también los ingresos, de tal manera de llevar un control de gastos y evitar gastar más de lo que ingresa por mes."
*   **Roadmap (Fase 2):**
    *   `[ ]` **Diseño de Base de Datos Escalable (¡Nuevo!):** Modificar la estructura de la base de datos para soportar múltiples orígenes de datos (bancos, tiendas), tipos de transacciones (ingresos/egresos) y la nueva categorización jerárquica.
    *   `[ ]` **Soporte Multi-Origen:** Añadir la capacidad de procesar boletas y cartolas de bancos, otras tiendas, tarjetas de crédito, etc.
    *   `[ ]` **Manejo de Ingresos (¡Nuevo!):** Implementar la lógica para identificar y registrar transacciones de ingresos.
    *   `[ ]` **Categorización Jerárquica:** Implementar un sistema de dos niveles: Categorías principales (ej. "Vivienda", "Transporte", "Alimentación") y sub-categorías (ej. "Supermercado", "Restaurantes", "Metro").
    *   `[ ]` **Organización de Archivos:** Clasificar los archivos PDF/CSV descargados en carpetas según su origen.
    *   `[ ]` **Dashboard Financiero (¡Nuevo!):** Crear un panel principal que muestre el balance mensual (ingresos vs. gastos), gráficos por categoría y alertas.
    *   `[ ]` **Sistema de Alertas y Presupuestos:** Crear notificaciones para gastos no categorizados, consumos que superen un límite predefinido, etc.
    *   `[ ]` **Interfaz Gráfica (GUI) Unificada:** Evolucionar la GUI de la Fase 1 para que soporte todas las nuevas funcionalidades (múltiples orígenes, ingresos, dashboard, etc.).
