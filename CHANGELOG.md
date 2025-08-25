# Historial de Cambios

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
- Se ajustó la expresión regular `CANTIDAD_PRECIO` en `config.py` para manejar espacios en blanco iniciales, resolviendo un error de aserción en `test_process_pdf_success`.
- Se configuró `conftest.py` para asegurar la correcta importación de módulos en el entorno de pruebas. (5485913)
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
