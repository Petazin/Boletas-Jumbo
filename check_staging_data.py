import mysql.connector
import sys
from config import DB_CONFIG

def check_staging_tables(target_table=None):
    """Verifica los datos insertados en las tablas staging."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        if target_table:
            staging_tables = [target_table]
        else:
            staging_tables = [
                'staging_cta_corriente_banco_de_chile',
                'staging_tarjeta_credito_banco_de_chile_nacional',
                'staging_tarjeta_credito_banco_de_chile_internacional',
                'staging_tarjeta_credito_falabella_nacional',
                'staging_cta_corriente_falabella',
                'staging_linea_credito_falabella',
                'staging_boletas_jumbo'
            ]
        
        print("=== VERIFICACIÓN DE TABLAS STAGING ===\n")
        
        for table in staging_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                print(f"[TABLA] {table}:")
                print(f"   Total registros: {count}")
                
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                    recent_records = cursor.fetchall()
                    print(f"   Primeros 3 registros:")
                    for record in recent_records:
                        print(f"     - {record}")
                
                print()  # Línea en blanco
                
            except mysql.connector.Error as e:
                if e.errno == 1146: # Table doesn't exist
                    print(f"[INFO] La tabla {table} no existe. Omitiendo.")
                else:
                    print(f"[ERROR] Error consultando {table}: {e}")
                print()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Error conectando a la base de datos: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_staging_tables(sys.argv[1])
    else:
        check_staging_tables()
