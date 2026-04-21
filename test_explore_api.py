import requests
import os

API_URL = "http://localhost:8000/api/v1/files/upload"
FILE_PATH = "ingesta_masiva/Banco_Chile/Cartola_LC/01022026_Cartola-Emitida-Cuenta.pdf"

def explore():
    print(f"Probando carga a través de la API: {FILE_PATH}")
    if not os.path.exists(FILE_PATH):
        print("El archivo no existe localmente.")
        return

    with open(FILE_PATH, "rb") as f:
        files = {"file": (os.path.basename(FILE_PATH), f, "application/pdf")}
        data = {
            "origen": "Banco_Chile",
            "tipo_doc": "Cartola_LC", 
            "password": "" 
        }
        
        print("Enviando POST...")
        # Aumentamos agresivamente timeout dado que la IA local es lenta
        response = requests.post(API_URL, files=files, data=data, timeout=600)
        
        print(f"STATUS CODE: {response.status_code}")
        if response.status_code == 200:
            print("RESPUESTA JSON:")
            print(response.json())
        else:
            print("ERROR RESPUESTA:")
            print(response.text)

if __name__ == "__main__":
    explore()
