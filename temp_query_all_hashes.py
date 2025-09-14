import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database_utils import db_connection

with db_connection() as conn:
    cursor = conn.cursor()
    query = "SELECT file_hash, nombre_archivo_original, document_type FROM raw_metadatos_documentos"
    cursor.execute(query)
    results = cursor.fetchall()
    if results:
        print("All entries in raw_metadatos_documentos:")
        for row in results:
            print(f"  Hash: {row[0]}, File: {row[1]}, Type: {row[2]}")
    else:
        print("No entries found in raw_metadatos_documentos.")
