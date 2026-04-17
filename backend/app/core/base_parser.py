import os
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import shutil
from datetime import datetime
from .image_utils import pdf_to_base64_images
from ..services.ai_service import AIService
from .exceptions import PasswordRequiredError, InvalidPasswordError

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    def __init__(self, db_connection, storage_path: str):
        self.db = db_connection
        self.storage_path = storage_path
        self.archivo_id = None
        self.file_hash = None
        self.ai_service = AIService()
        self.current_password = None

    def _calculate_hash(self, file_content: bytes) -> str:
        """Calcula el hash SHA256 del contenido del archivo."""
        return hashlib.sha256(file_content).hexdigest()

    def _is_duplicate(self, file_hash: str) -> bool:
        """Verifica si el archivo ya existe en la base de datos."""
        cursor = self.db.cursor()
        cursor.execute("SELECT archivo_id FROM archivos_fuente WHERE hash_archivo = %s", (file_hash,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None

    def _register_file(self, filename: str, file_hash: str, tipo_doc: str, origen: str) -> int:
        """Registra el archivo en la tabla archivos_fuente para trazabilidad."""
        cursor = self.db.cursor()
        sql = """
            INSERT INTO archivos_fuente 
            (nombre_original, nombre_almacenamiento, hash_archivo, tipo_documento, origen, extension, ruta_backup)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        ext = os.path.splitext(filename)[1].replace(".", "")
        nombre_almacenamiento = f"{tipo_doc}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_hash[:8]}.{ext}"
        ruta_backup = os.path.join("storage/originals", nombre_almacenamiento)

        values = (filename, nombre_almacenamiento, file_hash, tipo_doc, origen, ext, ruta_backup)
        cursor.execute(sql, values)
        last_id = cursor.lastrowid
        cursor.close()
        return last_id

    def _get_stored_password(self, origen: str, tipo_doc: str) -> str:
        """Busca en el llavero de la DB si ya existe una contraseña para este tipo de documento."""
        cursor = self.db.cursor()
        sql = "SELECT password_pdf FROM credenciales_archivadores WHERE origen = %s AND tipo_documento = %s"
        cursor.execute(sql, (origen, tipo_doc))
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None

    def _update_stored_password(self, origen: str, tipo_doc: str, password: str):
        """Guarda o actualiza la contraseña exitosa en el llavero de la DB."""
        if not password: return
        cursor = self.db.cursor()
        sql = """
            INSERT INTO credenciales_archivadores (origen, tipo_documento, password_pdf) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE password_pdf = VALUES(password_pdf)
        """
        cursor.execute(sql, (origen, tipo_doc, password))
        self.db.commit()
        cursor.close()
        logger.info(f"Contraseña guardada/actualizada para {origen} - {tipo_doc}")

    @abstractmethod
    def parse(self, file_content: bytes, password: str = None) -> Dict[str, Any]:
        """Método abstracto para extraer datos específicos del archivo."""
        pass

    @abstractmethod
    def save_to_staging(self, data: Dict[str, Any]):
        """Método abstracto para guardar datos crudos en la Capa 1."""
        pass

    @abstractmethod
    def consolidate(self):
        """Método abstracto para limpiar y mover datos a la Capa 2 (Consolidada)."""
        pass

    def run(self, filename: str, file_content: bytes, tipo_doc: str, origen: str, password: str = None):
        """Orquestador principal del flujo del parser con soporte de contraseñas."""
        self.file_hash = self._calculate_hash(file_content)

        if self._is_duplicate(self.file_hash):
            logger.warning(f"Archivo duplicado omitido: {filename}")
            return {"status": "duplicate", "message": "El archivo ya ha sido procesado anteriormente."}

        # 1. Resolver Contraseña (Manual > Llavero)
        self.current_password = password if password else self._get_stored_password(origen, tipo_doc)
        
        try:
            # 2. Registrar (Capa 0)
            self.archivo_id = self._register_file(filename, self.file_hash, tipo_doc, origen)
            
            # Guardar físicamente
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("SELECT ruta_backup FROM archivos_fuente WHERE archivo_id = %s", (self.archivo_id,))
            ruta = cursor.fetchone()['ruta_backup']
            cursor.close()

            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "wb") as f:
                f.write(file_content)

            # 3. Parsear (Extracción)
            logger.info(f"Procesando archivo {filename} con origen {origen}")
            extracted_data = self.parse(file_content, password=self.current_password)

            # 4. Guardar en Staging (Capa 1)
            self.save_to_staging(extracted_data)

            # 5. Consolidar (Capa 2)
            self.consolidate()

            # 6. ÉXITO: Guardar la contraseña que funcionó para el futuro
            if self.current_password:
                self._update_stored_password(origen, tipo_doc, self.current_password)

            return {
                "status": "success",
                "archivo_id": self.archivo_id,
                "message": f"Archivo {filename} procesado y consolidado exitosamente."
            }

        except (PasswordRequiredError, InvalidPasswordError) as e:
            # Errores de contraseña: No hacemos rollback, devolvemos error específico
            logger.warning(f"Error de seguridad en {filename}: {str(e)}")
            return {"status": "security_error", "error_code": type(e).__name__, "message": str(e)}
        except Exception as e:
            logger.error(f"Error procesando {filename}: {str(e)}")
            if self.db:
                self.db.rollback()
            return {"status": "error", "message": str(e)}
