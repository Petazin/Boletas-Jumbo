import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database_utils import db_connection

with db_connection() as conn:
    cursor = conn.cursor()
    query = "SELECT file_hash, nombre_archivo_original FROM raw_metadatos_documentos WHERE document_type = %s"
    cursor.execute(query, ('BOLETA_JUMBO',))
    results = cursor.fetchall()
    if results:
        print("Found Jumbo receipt hashes in raw_metadatos_documentos:")
        for row in results:
            print(f"  Hash: {row[0]}, File: {row[1]}")
    else:
        print("No Jumbo receipt hashes found in raw_metadatos_documentos.")
