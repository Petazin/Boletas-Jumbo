# Historial de Cambios

## [v1.1.0] - 2025-08-23

### Mejoras
- Se ha refactorizado el sistema de descarga y procesamiento de archivos para mejorar la escalabilidad y robustez del proyecto.
- Se introduce una tabla `download_history` en la base de datos para llevar un registro centralizado de todos los archivos descargados, su origen y su estado de procesamiento.
- El script `download_boletas.py` ahora utiliza la tabla `download_history` para evitar descargas duplicadas.
- Los archivos descargados son renombrados con un formato estandarizado que incluye la fecha de la compra (`{order_id}_{YYYY-MM-DD}.pdf`).
- Los archivos son guardados en una estructura de directorios organizada (`descargas/Jumbo/`).
- El script `process_boletas.py` ha sido actualizado para leer los archivos desde el nuevo directorio organizado y utilizar la tabla `download_history` para determinar qué archivos procesar.
- Se han mejorado y añadido comentarios en español en todos los archivos modificados para una mejor mantenibilidad.

## [v1.1.1] - 2025-08-25

### Mejoras
- Se ha mejorado la calidad del código y el formato en varios archivos del proyecto, siguiendo las directrices de estilo de Flake8.