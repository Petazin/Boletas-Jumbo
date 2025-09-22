import sys
import os
import argparse
import pandas as pd

# Añadir el directorio 'src' al sys.path para resolver las importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.database_utils import db_connection

def execute_query(query):
    """Ejecuta una consulta SQL y muestra los resultados en un formato tabular."""
    try:
        with db_connection() as conn:
            print(f"Ejecutando consulta: \"{query}\"")
            # Usar pandas para leer la consulta y mostrar un formato amigable
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("La consulta no devolvió resultados.")
            else:
                print("Resultados de la consulta:")
                print(df.to_string())

    except Exception as e:
        print(f"Ocurrió un error al ejecutar la consulta: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Ejecuta una consulta SQL en la base de datos del proyecto.')
    parser.add_argument('-q', '--query', type=str, required=True,
                        help='La consulta SQL a ejecutar.')
    
    args = parser.parse_args()
    
    execute_query(args.query)
