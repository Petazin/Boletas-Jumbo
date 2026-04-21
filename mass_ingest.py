import os
import requests

API_URL = "http://localhost:8000/api/v1/files/upload"
BASE_DIR = "ingesta_masiva"

def main():
    if not os.path.exists(BASE_DIR):
        print(f"Creando directorio base '{BASE_DIR}'.")
        print("Estructura requerida: ingesta_masiva/<origen>/<tipo_doc>/<archivo.pdf>")
        print("Ejemplo: ingesta_masiva/Falabella/Cartola_CC/enero.pdf")
        os.makedirs(BASE_DIR)
        print("Por favor, mueve tus PDFs a las carpetas correspondientes y vuelve a ejecutar este script.")
        return

    # Orígenes y tipos de documentos válidos según la BD
    valid_origenes = ['Banco_Chile', 'Falabella', 'Jumbo', 'Lider', 'Otro']
    valid_tipos = ['Cartola_CC', 'Cartola_TC', 'Cartola_LC', 'Boleta_Supermercado', 'Otro']

    archivos_procesados = 0

    for origen in os.listdir(BASE_DIR):
        origen_path = os.path.join(BASE_DIR, origen)
        if not os.path.isdir(origen_path): continue
        if origen not in valid_origenes:
            print(f"ADVERTENCIA: '{origen}' no es un origen válido en BD. Omitiendo.")
            continue

        for tipo_doc in os.listdir(origen_path):
            tipo_doc_path = os.path.join(origen_path, tipo_doc)
            if not os.path.isdir(tipo_doc_path): continue
            if tipo_doc not in valid_tipos:
                print(f"ADVERTENCIA: '{tipo_doc}' no es un tipo de documento válido. Omitiendo.")
                continue

            for archivo in os.listdir(tipo_doc_path):
                file_path = os.path.join(tipo_doc_path, archivo)
                if not os.path.isfile(file_path): continue
                if not file_path.lower().endswith(".pdf"): continue

                print(f"\nProcesando: {archivo} ({origen} - {tipo_doc})")
                if upload_file(file_path, origen, tipo_doc):
                    archivos_procesados += 1

    if archivos_procesados == 0:
        print("\nNo se encontraron archivos PDF para procesar.")
    else:
        print(f"\n¡Se procesaron {archivos_procesados} archivos exitosamente!")

def upload_file(file_path, origen, tipo_doc, password=None):
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/pdf")}
        data = {
            "origen": origen,
            "tipo_doc": tipo_doc
        }
        if password:
            data["password"] = password
            
        try:
            print("  -> Enviando al backend...")
            # Un timeout generoso porque la IA local puede demorar procesando cada página
            response = requests.post(API_URL, files=files, data=data, timeout=600) 
            
            if response.status_code == 200:
                print(f"  [EXITO] {response.json().get('message')}")
                return True
            elif response.status_code == 401 or "PASSWORD_REQUIRED" in response.text:
                print(f"  [CLAVE REQUERIDA] El archivo está protegido y el Llavero Local no tiene la contraseña para {origen} - {tipo_doc}.")
                pw = input("  Ingrese la contraseña para este tipo de documento: ")
                print("  (Se intentará nuevamente guardando la clave en el llavero...)")
                return upload_file(file_path, origen, tipo_doc, password=pw)
            else:
                print(f"  [ERROR] {response.status_code}: {response.text}")
                return False
        except requests.exceptions.ConnectionError:
             print("  [ERROR] No se pudo conectar al servidor. Asegúrate de que los contenedores Docker estén corriendo (puerto 8000).")
             return False
        except requests.exceptions.Timeout:
             print("  [ERROR] Tiempo de espera agotado. El archivo tomó demasiado en procesarse.")
             return False

if __name__ == "__main__":
    main()
