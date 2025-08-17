import pandas as pd
import logging
import mysql.connector

# Importar utilidades y configuración
from config import EXPORT_CSV_FILE
from database_utils import db_connection

def main():
    """Exporta la tabla boletas_data a un archivo CSV."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Usar el manejador de contexto para la conexión
        with db_connection() as conn:
            query = "SELECT * FROM boletas_data"
            
            logging.info("Ejecutando consulta para obtener datos de la tabla...")
            df = pd.read_sql(query, conn)
        
        logging.info(f"Se encontraron {len(df)} filas. Guardando en {EXPORT_CSV_FILE}...")
        df.to_csv(EXPORT_CSV_FILE, index=False, encoding='utf-8-sig')
        
        logging.info(f"¡Éxito! Los datos han sido exportados a {EXPORT_CSV_FILE}")

    except mysql.connector.Error as db_err:
        # El error de DB ya se loguea en db_connection, aquí solo se notifica el fallo de la exportación.
        logging.error(f"La exportación falló debido a un error en la base de datos.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante la exportación: {e}")

if __name__ == "__main__":
    main()
