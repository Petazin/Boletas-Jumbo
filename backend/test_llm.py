import base64
from openai import OpenAI
import httpx

client = OpenAI(base_url="http://host.docker.internal:1234/v1", api_key="test")

prompt = """
Eres un asistente de contabilidad experto.
Busca la tabla "DETALLE DE MOVIMIENTOS" en la imagen. Tiene columnas: FECHA, DETALLE DE TRANSACCION, SUCURSAL, MONTO CHEQUES O CARGOS, MONTO DEPOSITOS O ABONOS.
Debes extraer todas las filas desde el primer movimiento hasta llegar al SALDO FINAL.

Usa este formato exacto:
FECHA | DETALLE | MONTO | TIPO | CATEGORIA

Ejemplo conceptual:
02/01 | COMPRA | 1000 | Gasto | Otros

Extrae todas las filas que existan.
"""

# Read the image
try:
    with open("/app/app/debug_images/debug_page_1.jpg", "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
except Exception as e:
    print("No image found:", e)
    exit()

print("Enviando petición...")
response = client.chat.completions.create(
    model="local-model",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        }
    ],
    temperature=0.0
)

print("\n--- RESPUESTA ---")
print(response.choices[0].message.content)
