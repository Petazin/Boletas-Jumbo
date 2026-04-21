import mysql.connector

def reset_database():
    print("Conectando a la base de datos para limpiar tablas...")
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=3307,
            user="zenith_user",
            password="zenith_pass_2026",
            database="zenith_finance"
        )
        cursor = conn.cursor()
        
        # Desactivamos comprobación de foráneas
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        tablas_a_limpiar = [
            "items_compra",
            "transacciones_consolidadas",
            "staging_falabella",
            "staging_banco_chile",
            "metadatos_documento",
            "archivos_fuente"
        ]
        
        for tabla in tablas_a_limpiar:
            cursor.execute(f"TRUNCATE TABLE {tabla};")
            print(f" - Tabla '{tabla}' limpiada.")
            
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        
        print("\n✅ Base de datos restaurada al estado original con éxito.")
        
    except Exception as e:
        print(f"❌ Error al limpiar la BD: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    reset_database()
