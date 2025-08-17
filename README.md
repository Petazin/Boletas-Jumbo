# Proyecto de Finanzas Personales

## Visión del Proyecto

El objetivo final es construir una aplicación integral para la gestión de finanzas personales. El desarrollo se dividirá en dos fases principales:

1.  **Fase 1:** Perfeccionar un analizador de boletas de supermercado (Jumbo) para extraer y analizar datos de consumo.
2.  **Fase 2:** Expandir la aplicación para que sea un gestor financiero completo, capaz de procesar cualquier tipo de boleta o cartola, controlar gastos e ingresos, y ayudar a mantener un presupuesto mensual saludable.

---

## Fase 1: Analizador de Boletas de Supermercado (Jumbo)

*   **Objetivo:** "Crear una aplicación que pueda analizar boletas del supermercado JUMBO, guardando en una base de datos la información para luego usar de manera analítica los datos extraídos."
*   **Funcionalidades Actuales:**
    *   **1. Descarga Automatizada (`download_boletas.py`)**
        *   Utiliza **Selenium** para controlar un navegador Chrome y acceder a `Jumbo.cl`.
        *   **Requiere intervención manual:** El usuario debe iniciar sesión en su cuenta.
        *   Navega automáticamente a la sección "Mis Compras".
        *   Recorre el historial de compras y descarga las boletas en formato **PDF**.
        *   Verifica si una boleta ya fue descargada para evitar duplicados.
        *   Genera un registro de actividad en `download_boletas.log`.
    *   **2. Procesamiento y Extracción de Datos (`process_boletas.py`)**
        *   Escanea la carpeta del proyecto en busca de archivos PDF.
        *   **Extracción de Texto:** Usa `PyPDF2` para leer el contenido de cada boleta.
        *   **Análisis con Expresiones Regulares (Regex):**
            *   Extrae datos clave de la boleta como el **N° de Boleta** y la **Fecha de Compra**.
            *   Identifica cada producto, extrayendo SKU, descripción, cantidad, precio unitario y descuentos aplicados.
        *   **Categorización de Productos:**
            *   Cada producto es clasificado automáticamente en una categoría (ej. "Lácteos y Huevos", "Higiene Personal", "Mascotas") según palabras clave en su descripción.
        *   **Base de Datos MySQL:**
            *   Se conecta a una base de datos local llamada `Boletas`.
            *   Crea (si no existe) y utiliza una tabla `boletas_data` para almacenar la información.
            *   Guarda cada producto como un registro individual en la base de datos, evitando duplicados si un archivo ya fue procesado.
        *   Genera un registro detallado del proceso en `process_boletas.log`.
    *   **3. Exportación de Datos (`export_data.py`)**
        *   Se conecta a la base de datos `Boletas`.
        *   Utiliza la librería **Pandas** para leer todos los datos de la tabla `boletas_data`.
        *   Exporta la información consolidada a un archivo **CSV** llamado `boletas_data.csv`, listo para ser analizado en Excel u otras herramientas.
*   **Roadmap (Fase 1):**
    *   `[ ]` **Mejora de Categorización Actual:** Revisar y refinar las reglas de categorización para reducir la cantidad de productos en la categoría "Otros".
    *   `[ ]` **Generar Gráficos y Estadísticas:** Crear visualizaciones básicas (ej. gasto por categoría, gasto en el tiempo) a partir de los datos de Jumbo.
    *   `[ ]` **Interfaz Gráfica (GUI) para Jumbo:** Desarrollar una interfaz de usuario simple para ejecutar los scripts actuales (descarga, proceso, exportación) sin usar la línea de comandos.

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