import requests
import os

API_URL = "http://localhost:8000/api/v1/files/upload"
FILE_PATH = "archivos_prueba/ECBF_CC_202602_01-983-168032-7.pdf"

def test_autofill_keychain():
    print(f"Probando Auto-Llenado de Clave para: {FILE_PATH} (Sin Password)")
    if not os.path.exists(FILE_PATH):
        print(f"ERROR: No se encuentra el archivo en {FILE_PATH}")
        return

    with open(FILE_PATH, "rb") as f:
        # Nota: NO enviamos el campo 'password'
        files = {"file": (os.path.basename(FILE_PATH), f, "application/pdf")}
        data = {
            "origen": "Falabella",
            "tipo_doc": "Cartola_CC"
        }
        
        response = requests.post(API_URL, files=files, data=data)
        
        if response.status_code == 200:
            print("RESPUESTA RECIBIDA:")
            print(response.json())
        else:
            print(f"ERROR ({response.status_code}):")
            print(response.text)

if __name__ == "__main__":
    test_autofill_keychain()
