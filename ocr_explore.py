import io
import pytesseract
from PIL import Image
import base64
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from app.core.image_utils import pdf_to_base64_images

pdf_path = "ingesta_masiva/Banco_Chile/Cartola_LC/01012026_Cartola-Emitida-Cuenta.pdf"
with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

images = pdf_to_base64_images(pdf_bytes, password=None) 
if not images:
    print("No images")
    sys.exit()

img_data = base64.b64decode(images[0])
img = Image.open(io.BytesIO(img_data))
text_page = pytesseract.image_to_string(img, lang='spa')
print(text_page)
