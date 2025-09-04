import mysql.connector
from config import DB_CONFIG

def clean_test_file():
    """Limpia los registros de un archivo específico para poder volver a procesarlo."""
    test_hash = "a729566222e1f0e43038c1014c907f584d524dc2630182b2b41536d8e4497164"
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Buscar metadata_id
        cursor.execute("SELECT metadata_id FROM metadatos_cartolas_bancarias_raw WHERE file_hash = %s", (test_hash,))
        result = cursor.fetchone()
        
        if not result:
            print("[INFO] No se encontró el archivo en la BD")
            return
        
        metadata_id = result[0]
        print(f"[INFO] Encontrado metadata_id: {metadata_id}")
        
        # Eliminar de tablas relacionadas
        cursor.execute("DELETE FROM tarjeta_credito_banco_de_chile_internacional_staging WHERE metadata_id = %s", (metadata_id,))
        staging_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM transacciones_tarjeta_credito_raw WHERE metadata_id = %s", (metadata_id,))
        transactions_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM metadatos_cartolas_bancarias_raw WHERE metadata_id = %s", (metadata_id,))
        metadata_deleted = cursor.rowcount
        
        conn.commit()
        
        print(f"[INFO] Eliminados: {staging_deleted} staging, {transactions_deleted} transacciones, {metadata_deleted} metadatos")
        print("[SUCCESS] Archivo limpiado para reprocesamiento")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Error limpiando archivo: {e}")

if __name__ == "__main__":
    clean_test_file()