import requests
import os

API_URL = "http://localhost:8000/api/v1/files/upload"
FILE_PATH = "archivos_prueba/ECBF_CC_202602_01-983-168032-7.pdf"
PASSWORD = "159486214"

def test_falabella():
    print(f"Probando carga de Falabella: {FILE_PATH} con clave")
    if not os.path.exists(FILE_PATH):
        print(f"ERROR: No se encuentra el archivo en {FILE_PATH}")
        return

    with open(FILE_PATH, "rb") as f:
        files = {"file": (os.path.basename(FILE_PATH), f, "application/pdf")}
        data = {
            "origen": "Falabella",
            "tipo_doc": "Cartola_CC",
            "password": PASSWORD
        }
        
        response = requests.post(API_URL, files=files, data=data)
        
        if response.status_code == 200:
            print("RESPUESTA RECIBIDA:")
            print(response.json())
        else:
            print(f"ERROR ({response.status_code}):")
            print(response.text)

if __name__ == "__main__":
    test_falabella()
