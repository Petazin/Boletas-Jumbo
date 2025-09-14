
import mysql.connector
from database_utils import db_connection

def test_sql_conversion():
    """
    Prueba la lógica de conversión de cadenas a decimal en SQL para validar la teoría
    de que el método actual es insuficiente.
    """
    test_cases = {
        "Entero (ej: 12345)": "12345",
        "Con separador de miles (ej: 12.345)": "12.345",
        "Con decimales (ej: 123,45)": "123,45",
        "Con miles y decimales (ej: 12.345,67)": "12.345,67"
    }

    print("--- INICIANDO PRUEBA DE LÓGICA DE CONVERSIÓN SQL ---")
    
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            for description, value in test_cases.items():
                print(f"\n--- Caso de Prueba: {description} ---")
                print(f"Valor de entrada: '{value}'")

                # Lógica actual (potencialmente incorrecta)
                try:
                    query_actual = "SELECT CAST(REPLACE(%s, '.', '') AS DECIMAL(15,2))"
                    cursor.execute(query_actual, (value,))
                    resultado_actual = cursor.fetchone()[0]
                    print(f"  Lógica ACTUAL -> Resultado: {resultado_actual}")
                except mysql.connector.Error as err:
                    print(f"  Lógica ACTUAL -> ERROR: {err}")

                # Lógica propuesta (más robusta)
                try:
                    query_propuesta = "SELECT CAST(REPLACE(REPLACE(%s, '.', ''), ',', '.') AS DECIMAL(15,2))"
                    cursor.execute(query_propuesta, (value,))
                    resultado_propuesto = cursor.fetchone()[0]
                    print(f"  Lógica PROPUESTA -> Resultado: {resultado_propuesto}")
                except mysql.connector.Error as err:
                    print(f"  Lógica PROPUESTA -> ERROR: {err}")

    except mysql.connector.Error as err:
        print(f"\nERROR de conexión a la base de datos: {err}")
    except Exception as e:
        print(f"\nOcurrió un error inesperado: {e}")

    print("\n--- PRUEBA FINALIZADA ---")

if __name__ == "__main__":
    test_sql_conversion()
