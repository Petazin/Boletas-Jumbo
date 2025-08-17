import pandas as pd
import mysql.connector
import logging

# Importar desde el archivo de configuración central
from config import DB_CONFIG, EXPORT_CSV_FILE

def main():
    """Exporta la tabla boletas_data a un archivo CSV."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        logging.info(f"Conectando a la base de datos '{DB_CONFIG['database']}'...")
        conn = mysql.connector.connect(**DB_CONFIG)
        
        query = "SELECT * FROM boletas_data"
        
        logging.info(f"Ejecutando consulta para obtener datos de la tabla...")
        df = pd.read_sql(query, conn)
        
        logging.info(f"Se encontraron {len(df)} filas. Guardando en {EXPORT_CSV_FILE}...")
        df.to_csv(EXPORT_CSV_FILE, index=False, encoding='utf-8-sig')
        
        logging.info(f"¡Éxito! Los datos han sido exportados a {EXPORT_CSV_FILE}")

    except Exception as e:
        logging.error(f"Ocurrió un error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    main()