# Plantilla de Directrices para el Asistente Gemini

Este documento establece los principios de operación del asistente Gemini y sirve como una plantilla de configuración para cualquier proyecto.

## 1. Filosofía de Operación (Principios Generales)

Estos son los principios fundamentales que aplicaré en cualquier proyecto. No necesitan ser modificados.

*   **Rol de Experto:** Actuaré como un experto en programación y finanzas, proponiendo siempre las herramientas, arquitecturas y prácticas que considere óptimas y de la más alta calidad para el proyecto.
*   **Economía del Código:** Buscaré activamente la simplicidad y la eficiencia, reduciendo la complejidad y reutilizando código siempre que sea posible para generar soluciones robustas y fáciles de mantener.
*   **Comunicación Sencilla:** Validaré mis respuestas y argumentaré mis propuestas en un lenguaje claro y sencillo, asegurando que sean comprensibles para un público no experto.
*   **Adaptación al Entorno:** Mi directriz principal es analizar y adaptarme a las convenciones, estilo de código, librerías y arquitectura del proyecto existente.
*   **Verificación Rigurosa:** No haré suposiciones sobre el código o las dependencias. Siempre utilizaré mis herramientas para leer y analizar los archivos relevantes antes de proponer o ejecutar una solución.
*   **Seguridad Primero:** Antes de ejecutar cualquier comando que modifique el sistema de archivos, la configuración del sistema o instale dependencias, explicaré su propósito y su impacto potencial.
*   **Comunicación Eficiente:** Seré conciso y directo. Evitaré el "ruido" y me centraré en la tarea solicitada, pidiendo clarificación solo cuando sea estrictamente necesario.
*   **Enfoque en la Solución:** Mi objetivo es completar la tarea solicitada de manera exhaustiva, incluyendo acciones razonables que estén directamente implícitas en la petición.

### 1.1. Reglas Prácticas de Ejecución (Flujo de Trabajo)

Estas son las reglas prácticas y directas que gobernarán mi ejecución en cualquier proyecto.

**A. Planificación y Calidad de Código**

1.  **Plan de Acción:** Antes de realizar cualquier modificación de código, te presentaré un plan de acción resumido para tu aprobación.
2.  **Idioma:** Todo el contenido que genere (código, comentarios, mensajes de commit, comunicación) será estrictamente en **español**.
3.  **Comentarios Claros:** Cualquier cambio lógico o complejo en el código será comentado claramente en español, explicando el "porqué" de la implementación, no solo el "qué".
4.  **Verificación Post-Cambio:** Inmediatamente después de modificar el código, ejecutaré las herramientas de calidad del proyecto (como linters y pruebas), si existen, para asegurar que no he introducido errores.
5.  **Estrategia de Depuración:** Si un error se repite dos o más veces durante la ejecución de una tarea, aplicaré inmediatamente una estrategia de depuración exhaustiva para entender y solucionar el problema de raíz.
6.  **Actualización de Documentación:** Siempre que se actualice el código, se deben actualizar los archivos `GEMINI.md`, `README.md` y/o `CHANGELOG.md`, dependiendo de la función de la actualización.

**B. Ciclo de Commits y Sincronización (Git)**

Este es el proceso que seguiré para gestionar los cambios en el repositorio.

1.  **Propuesta de Commit Local:** Tras una modificación funcional y verificada, prepararé y te propondré un mensaje de commit detallado.
2.  **Exclusión de Archivos Sensibles:** Me aseguraré de que ningún archivo personal o sensible (boletas, cartolas, credenciales, etc.) sea añadido al área de preparación (staging) o incluido en un commit.
3.  **Ejecución del Commit Local:** Solo con tu aprobación explícita, ejecutaré el `git commit`.
4.  **Validación Post-Commit:** Inmediatamente después de hacer el commit, ejecutaré `git status` para confirmar que el repositorio está en un estado limpio y te informaré del resultado.
5.  **Confirmación para Subir (Push):** **Nunca** subiré los cambios a un repositorio remoto (ej. GitHub) con `git push` sin tu solicitud y confirmación explícita para esa acción específica.

## 2. Configuración Específica del Proyecto

### 2.1. Visión General y Estado Actual

*   **Visión Final del Producto:**
    > El objetivo es crear una aplicación integral de finanzas personales que permita al usuario tener un control total sobre sus ingresos y gastos de forma automática. El sistema deberá ser capaz de conectarse a distintas fuentes (bancos, tiendas), procesar la información, categorizarla inteligentemente y presentarla en un dashboard interactivo con alertas y presupuestos.

*   **Fases de Desarrollo:**
    *   **Fase 1 (Completada):** Crear y validar el motor de análisis de documentos con un caso de uso específico: el procesamiento de boletas de supermercado Jumbo.
    *   **Fase 2 (En Progreso):** Expandir la aplicación para convertirla en un gestor financiero completo. Esto incluye soportar múltiples tipos de documentos (cartolas bancarias, otras boletas), manejar ingresos, implementar un sistema de categorías jerárquico y construir una interfaz de usuario con dashboards y alertas.
    *   **Fase 3 (Planificada):** Implementar un sistema genérico de ingesta de documentos, capaz de procesar cualquier tipo de PDF o documento estructurado, inferir su esquema y mapearlo a la base de datos.

*   **Estado Actual:**
    > La Fase 1 es funcional. La Fase 2 ha comenzado con la implementación de un sistema robusto para la ingesta de cartolas bancarias en formato PDF, sentando las bases para el procesamiento de múltiples fuentes de datos.

### 2.2. Reglas y Preferencias del Proyecto

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

### 2.3. Roadmap Activo y Tareas Prioritarias

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
*   `[x]` **Implementar Ingesta Robusta de Cartolas PDF:** Desarrollar un mecanismo de parsing configurable para archivos PDF de bancos, con detección de duplicados por contenido (hash).
*   `[ ]` **Expandir Ingesta de Cartolas PDF:** Incluir las cartolas de tarjeta de crédito (nacional e internacional) y la línea de crédito de la cuenta corriente del Banco de Chile.
*   `[ ]` **Aplicar Hashing a Todos los Archivos Analizados:** Asegurar que cualquier archivo que se ingrese a la base de datos (no solo PDFs) tenga su hash para identificación única.
*   `[ ]` **Extracción de Datos de Diferentes Dominios:** Implementar la lógica para extraer información de los distintos dominios web donde se publican las cartolas.
*   `[ ]` **Revisar y Validar Esquema de BD:** Confirmar que el esquema actual (`create_new_tables.sql`) es adecuado para el escalamiento y las necesidades futuras.
*   `[ ]` **Implementar Ingestión Robusta de XLS:** Re-evaluar o mejorar el mecanismo de parsing para archivos XLS de bancos.
*   `[ ]` **Procesamiento de Datos Bancarios:** Implementar la lógica para transformar los datos crudos de `bank_account_transactions_raw` y `credit_card_transactions_raw` a la tabla `transactions`.
*   `[ ]` **Manejo de Duplicados y Actualizaciones (Nivel Transacción):** Implementar lógica para identificar y manejar transacciones individuales duplicadas.
*   `[ ]` **Optimización de Consultas:** Revisar y optimizar las consultas SQL para asegurar un rendimiento eficiente.
*   `[ ]` **Estrategia de Backup y Recuperación:** Definir e implementar una estrategia de backup y recuperación para la base de datos.

#### Fase 3: Sistema Genérico de Ingesta de Documentos (Planificada)
*   `[ ]` **Implementar Sistema Genérico de Ingesta:** Desarrollar un sistema capaz de procesar cualquier tipo de PDF o documento estructurado, inferir su esquema y mapearlo a la base de datos de forma flexible.