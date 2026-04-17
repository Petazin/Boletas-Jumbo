import requests
import os
import sys

# --- CONFIGURACIÓN ---
API_URL = "http://localhost:8000/api/v1/files/upload"
TEST_FOLDER = "archivos_prueba"

def get_files_in_test_folder():
    if not os.path.exists(TEST_FOLDER):
        os.makedirs(TEST_FOLDER)
    return [f for f in os.listdir(TEST_FOLDER) if os.path.isfile(os.path.join(TEST_FOLDER, f))]

def test_upload(file_path, origen, tipo_doc, password=None):
    print(f"\n--- Enviando: {os.path.basename(file_path)} ---")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            data = {
                "origen": origen,
                "tipo_doc": tipo_doc
            }
            if password:
                data["password"] = password
            
            response = requests.post(API_URL, files=files, data=data)
            
            if response.status_code == 200:
                res_data = response.json()
                # Verificar si el backend reporta un error de seguridad (aunque sea status 200)
                if res_data.get("status") == "error" or res_data.get("status") == "security_error":
                    print(f"⚠️ AVISO: {res_data.get('message')}")
                    # Si falta la clave o es inválida, pedirla y reintentar
                    new_pw = input("Introduce la contraseña del PDF: ")
                    return test_upload(file_path, origen, tipo_doc, password=new_pw)
                
                print(f"✅ ÉXITO: {res_data.get('message')}")
                return True
            else:
                print(f"❌ ERROR ({response.status_code}):")
                print(response.text)
                return False
                
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        return False

if __name__ == "__main__":
    print("===============================================")
    print("Zenith Finance - Consola de Ingesta Inteligente")
    print("===============================================")
    
    files = get_files_in_test_folder()
    
    if not files:
        print(f"\nLa carpeta '{TEST_FOLDER}' está vacía.")
        sys.exit()

    print("\nArchivos disponibles:")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
    
    try:
        idx = int(input("\nSelecciona el archivo: ")) - 1
        selected_file = os.path.join(TEST_FOLDER, files[idx])
        
        print("\nConfiguración:")
        print("1. Banco de Chile (PDF/Imagen)")
        print("2. Falabella (PDF/Excel)")
        
        opt = input("Selecciona origen (1 o 2): ")
        origen = "Banco_Chile" if opt == "1" else "Falabella"
        tipo_doc = "Cartola_CC" # Por defecto
        
        # Ejecutar
        test_upload(selected_file, origen, tipo_doc)
        
    except (ValueError, IndexError):
        print("Selección inválida.")
