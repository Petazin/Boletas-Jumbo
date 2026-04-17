from pdf2image import convert_from_bytes
from pdf2image.exceptions import PDFPageCountError
import io
import base64
import logging
from .exceptions import PasswordRequiredError, InvalidPasswordError

logger = logging.getLogger(__name__)

def pdf_to_base64_images(pdf_content: bytes, password: str = None):
    """
    Convierte un PDF en una lista de imágenes en formato base64.
    Soporta PDFs protegidos mediante el parámetro password.
    """
    try:
        # Convertir PDF a lista de imágenes (PIL objects)
        # userpw es el argumento de pdf2image para la contraseña
        images = convert_from_bytes(pdf_content, dpi=200, userpw=password)
        
        base64_images = []
        for i, img in enumerate(images):
            # Guardar para depuración física en el servidor (opcional)
            debug_path = f"/app/app/debug_images/debug_page_{i+1}.jpg"
            img.save(debug_path, format="JPEG", quality=85)

            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            base64_images.append(img_str)
            
        logger.info(f"PDF convertido a {len(base64_images)} imágenes.")
        return base64_images
        
    except PDFPageCountError as e:
        error_msg = str(e)
        if "Incorrect password" in error_msg:
            if password:
                logger.error("La contraseña proporcionada para el PDF es incorrecta.")
                raise InvalidPasswordError("La contraseña ingresada es incorrecta para este documento.")
            else:
                logger.error("El PDF requiere una contraseña que no fue proporcionada.")
                raise PasswordRequiredError("Este archivo está protegido. Por favor, ingresa la contraseña.")
        
        logger.error(f"Error de Poppler al contar páginas: {error_msg}")
        raise e
    except Exception as e:
        logger.error(f"Error inesperado convirtiendo PDF a imagen: {str(e)}")
        raise e
