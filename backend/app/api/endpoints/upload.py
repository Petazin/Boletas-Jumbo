from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from typing import Optional
from mysql.connector import MySQLConnection
from ...db import get_db
from ...parsers.banco_chile import BancoChileParser
from ...parsers.falabella import FalabellaParser
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    origen: str = Form(...), # Banco_Chile, Falabella, Jumbo
    tipo_doc: str = Form(...), # Cartola_CC, Cartola_TC, Boleta_Supermercado
    password: Optional[str] = Form(None), # Nuevo: Soporte para password manual
    db: MySQLConnection = Depends(get_db)
):
    """
    Endpoint para subir y procesar archivos de finanzas.
    Soporta resolución automática de contraseñas guardadas.
    """
    try:
        content = await file.read()
        
        # Fábrica de Parsers
        parser = None
        storage_path = "/app/storage" 

        if origen == "Banco_Chile":
            parser = BancoChileParser(db, storage_path)
        elif origen == "Falabella":
            parser = FalabellaParser(db, storage_path)
        else:
            raise HTTPException(status_code=400, detail=f"Origen '{origen}' no soportado aún.")

        # Ejecutar procesamiento con soporte de password
        result = parser.run(
            filename=file.filename, 
            file_content=content, 
            tipo_doc=tipo_doc, 
            origen=origen, 
            password=password
        )

        # Manejo de Errores Estructurados (Seguridad)
        if result["status"] == "security_error":
            logger.warning(f"Error de seguridad detectado: {result['error_code']}")
            return {
                "status": "error",
                "error_code": result["error_code"], # PasswordRequiredError o InvalidPasswordError
                "message": result["message"]
            }

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        if result["status"] == "duplicate":
            return {"status": "duplicate", "message": result["message"], "archivo_id": None}

        return {
            "status": "success",
            "message": "Archivo procesado exitosamente",
            "archivo_id": result["archivo_id"],
            "filename": file.filename
        }

    except Exception as e:
        logger.error(f"Error crítico en upload endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
