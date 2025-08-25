import logging
from database_utils import db_connection


def get_otros_productos():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            query = (
                "SELECT DISTINCT Descripcion_producto FROM boletas_data "
                "WHERE Categoria = 'Otros'"
            )
            cursor.execute(query)
            otros_productos = cursor.fetchall()

            if otros_productos:
                logging.info(
                    "\n--- Descripciones de productos en la categoría 'Otros' ---"
                )
                for producto in otros_productos:
                    print(producto[0])  # producto[0] contiene la descripción
                logging.info(
                    "----------------------------------------------------------"
                )
            else:
                logging.info("No se encontraron productos en la categoría 'Otros'.")

    except Exception as e:
        logging.error(f"Ocurrió un error al obtener productos 'Otros': {e}")


if __name__ == "__main__":
    get_otros_productos()
