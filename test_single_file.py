import os
import sys
import mysql.connector
from database_utils import db_connection

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingest_xls_international_cc import (
    calculate_file_hash, 
    is_file_processed, 
    get_source_id, 
    insert_metadata,
    process_international_cc_xls_file,
    insert_raw_international_cc_to_staging,
    insert_credit_card_transactions,
    load_abono_mappings
)

def test_single_file():
    """Prueba el procesamiento de un solo archivo para verificar la corrección."""
    test_file = r"C:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\tarjeta de credito\internacional\2025 Abril TCI BC Cartola-Emitida-Cuenta.xls"
    
    if not os.path.exists(test_file):
        print(f"[ERROR] Archivo no encontrado: {test_file}")
        return
    
    print(f"[INFO] Probando archivo: {os.path.basename(test_file)}")
    
    try:
        with db_connection() as conn:
            # Cargar mapeos de abonos
            abono_descriptions = load_abono_mappings(conn)
            print(f"[INFO] Cargados {len(abono_descriptions)} mapeos de abonos")
            
            # Verificar si ya fue procesado
            file_hash = calculate_file_hash(test_file)
            if is_file_processed(conn, file_hash):
                print(f"[INFO] Archivo ya procesado, hash: {file_hash}")
                return
            
            # Obtener source_id
            source_id = get_source_id(conn, 'Banco de Chile - Tarjeta Credito Internacional')
            print(f"[INFO] Source ID: {source_id}")
            
            # Insertar metadatos
            metadata_id = insert_metadata(conn, source_id, test_file, file_hash, 'International Credit Card Statement')
            print(f"[INFO] Metadata ID: {metadata_id}")
            
            # Procesar archivo
            result = process_international_cc_xls_file(test_file, source_id, metadata_id, abono_descriptions)
            
            if result is None:
                print("[ERROR] Error en el procesamiento")
                return
            
            raw_df, processed_df = result
            print(f"[INFO] Raw DataFrame: {len(raw_df)} filas, {len(raw_df.columns)} columnas")
            print(f"[INFO] Processed DataFrame: {len(processed_df)} filas, {len(processed_df.columns)} columnas")
            print(f"[INFO] Columnas Raw DF: {list(raw_df.columns)}")
            
            # Insertar en staging
            if raw_df is not None and not raw_df.empty:
                insert_raw_international_cc_to_staging(conn, metadata_id, source_id, raw_df)
                print("[SUCCESS] Datos insertados en staging correctamente")
            
            # Insertar transacciones procesadas
            if processed_df is not None and not processed_df.empty:
                insert_credit_card_transactions(conn, metadata_id, source_id, processed_df)
                print("[SUCCESS] Transacciones procesadas insertadas correctamente")
            
    except Exception as e:
        print(f"[ERROR] Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_file()