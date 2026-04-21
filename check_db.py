import os
import mysql.connector
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, '.env'))
conn = mysql.connector.connect(
    host="127.0.0.1", port=int(os.getenv("DB_PORT", 3307)),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME")
)
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT descripcion_limpia, monto, tipo FROM transacciones_consolidadas WHERE archivo_id = 4")
rows = cursor.fetchall()
print(f"Extraídas {len(rows)} filas:")
for r in rows:
    print(r)
