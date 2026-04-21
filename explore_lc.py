import os
import io
import sys
# Acomodar PYTHONPATH para poder importar módulos del backend
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.ai_service import AIService
from app.core.image_utils import pdf_to_base64_images

def explore():
    pdf_path = "ingesta_masiva/Banco_Chile/Cartola_LC/01012026_Cartola-Emitida-Cuenta.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Archivo no encontrado: {pdf_path}")
        return

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        
    print("Convirtiendo PDF a imagen...")
    # Asumo que pueden no tener password si son descargadas directo iniciadas sesion, o sí pueden tener.
    # Probemos sin password primero.
    try:
        images = pdf_to_base64_images(pdf_bytes, password=None) 
        print(f"Páginas convertidas: {len(images)}")
    except Exception as e:
        print(f"Error al leer PDF (quizá tiene clave?): {e}")
        return
    
    if not images:
        return

    ai = AIService()
    print("\n--- EXTRAYENDO METADATA ---")
    meta = ai.extract_metadata(images[0], origin="Banco_Chile")
    print(meta)
    
    print("\n--- EXTRAYENDO TRANSACCIONES (PÁGINA 1) ---")
    txs = ai.extract_transactions(images[0], origin="Banco_Chile", current_year="2026", text_content=None)
    for i, t in enumerate(txs):
        print(f"{i+1}: {t}")

if __name__ == "__main__":
    explore()
