import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database_utils import db_connection

def show_full_table(table_name):
    """Muestra todos los registros de una tabla."""
    try:
        with db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = f"SELECT * FROM {table_name}"
            print(f"Contenido de la tabla '{table_name}':")
            cursor.execute(query)
            results = cursor.fetchall()
            if results:
                for row in results:
                    print(row)
            else:
                print("La tabla está vacía.")
    except Exception as e:
        print(f"Ocurrió un error al consultar la tabla: {e}")

if __name__ == "__main__":
    show_full_table("historial_descargas")