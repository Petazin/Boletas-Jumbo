# -*- coding: utf-8 -*-
"""Script para exportar los datos de la base de datos a un archivo CSV."""

import pandas as pd
import logging
import mysql.connector

# Importar utilidades y configuración
from config import EXPORT_CSV_FILE
from database_utils import db_connection


def main():
    """Exporta la tabla completa 'boletas_data' a un archivo CSV."""
    # Configuración básica de logging para este script
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        # Usar el manejador de contexto para una conexión segura a la BD
        with db_connection() as conn:
            # Consulta SQL para seleccionar todos los datos de la tabla
            query = "SELECT * FROM boletas_data"

            logging.info("Ejecutando consulta para obtener datos de la tabla...")
            # Usar pandas para leer los resultados de la consulta
            # directamente en un DataFrame
            df = pd.read_sql(query, conn)

        logging.info(
            f"Se encontraron {len(df)} filas. Guardando en {EXPORT_CSV_FILE}..."
        )
        # Guardar el DataFrame a un archivo CSV.
        # index=False evita que pandas escriba el índice del DataFrame como una columna.
        # encoding='utf-8-sig' asegura la compatibilidad con caracteres
        # especiales (tildes, etc.) en Excel.
        df.to_csv(EXPORT_CSV_FILE, index=False, encoding="utf-8-sig")

        logging.info(f"¡Éxito! Los datos han sido exportados a {EXPORT_CSV_FILE}")

    except mysql.connector.Error:
        # El error de BD ya se loguea en db_connection, aquí solo se notifica el fallo.
        logging.error("La exportación falló debido a un error en la base de datos.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante la exportación: {e}")


if __name__ == "__main__":
    main()
