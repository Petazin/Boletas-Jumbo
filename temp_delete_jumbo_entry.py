import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database_utils import db_connection

file_hash_to_delete = "13012eacaed507c7e7ddcec02644572b24a1bf4b1d5cdda60c29f8350737a1d4"

with db_connection() as conn:
    cursor = conn.cursor()
    query = "DELETE FROM raw_metadatos_documentos WHERE file_hash = %s"
    cursor.execute(query, (file_hash_to_delete,))
    conn.commit()
    print(f"Deleted {cursor.rowcount} rows for hash {file_hash_to_delete}")
