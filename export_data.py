
import pandas as pd
import mysql.connector
import logging

# --- Configuración de la Base de Datos (igual que en process_boletas.py) ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456789',
    'database': 'Boletas'
}

OUTPUT_CSV_FILE = 'boletas_data.csv'

def main():
    """Exporta la tabla boletas_data a un archivo CSV."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        logging.info(f"Conectando a la base de datos '{DB_CONFIG['database']}'...")
        conn = mysql.connector.connect(**DB_CONFIG)
        
        query = "SELECT * FROM boletas_data"
        
        logging.info(f"Ejecutando consulta para obtener datos de la tabla...")
        # Usar pandas para leer la tabla directamente en un DataFrame
        df = pd.read_sql(query, conn)
        
        logging.info(f"Se encontraron {len(df)} filas. Guardando en {OUTPUT_CSV_FILE}...")
        # Guardar el DataFrame a un archivo CSV
        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        
        logging.info(f"¡Éxito! Los datos han sido exportados a {OUTPUT_CSV_FILE}")

    except Exception as e:
        logging.error(f"Ocurrió un error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    main()
