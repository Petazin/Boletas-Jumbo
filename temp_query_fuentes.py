from database_utils import db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_fuentes_data():
    """Obtiene y muestra todos los datos de la tabla 'fuentes'."""
    try:
        with db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM fuentes;"
            cursor.execute(query)
            records = cursor.fetchall()
            
            if not records:
                logging.info("La tabla 'fuentes' está vacía.")
                return

            logging.info("Datos en la tabla 'fuentes':")
            for record in records:
                logging.info(record)

            cursor.close()
    except Exception as e:
        logging.error(f'Error al consultar la tabla fuentes: {e}')

if __name__ == '__main__':
    get_fuentes_data()
