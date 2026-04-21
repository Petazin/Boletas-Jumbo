import pandas as pd
import io
import json
import logging
import hashlib
import base64
from typing import Dict, Any
from datetime import datetime
from ..core.base_parser import BaseParser
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

class FalabellaParser(BaseParser):
    def parse(self, file_content: bytes, password: str = None) -> Dict[str, Any]:
        """Extrae datos de cartolas de Falabella soportando XLS/XLSX y PDF (IA Two-Pass)."""
        
        if file_content.startswith(b'%PDF'):
            return self._parse_pdf(file_content, password=password)
        else:
            return self._parse_excel(file_content)

    def _parse_pdf(self, file_content: bytes, password: str = None) -> Dict[str, Any]:
        """Estrategia Two-Pass IA Vision + OCR Fallback para PDFs."""
        from ..core.image_utils import pdf_to_base64_images
        
        logger.info(f"Iniciando procesamiento Inteligente (PDF) para Falabella. Archivo ID: {self.archivo_id}")
        
        images = pdf_to_base64_images(file_content, password=password)
        if not images:
            raise ValueError("No se pudieron extraer imágenes del PDF de Falabella.")
            
        # Pass 1: Metadatos
        logger.info("--- Falabella Pass 1 (Metadata) ---")
        consolidated_metadata = self.ai_service.extract_metadata(images[0], "Falabella")
        
        year_to_use = str(datetime.now().year)
        if consolidated_metadata:
            p_desde = consolidated_metadata.get("periodo_desde", "")
            if p_desde and "-" in p_desde:
                year_to_use = p_desde.split("-")[0]
            elif p_desde and "/" in p_desde:
                parts = p_desde.split("/")
                if len(parts) >= 3:
                     y = parts[2]
                     year_to_use = f"20{y}" if len(y) == 2 else y

        # Extracción de texto (OCR Fallback)
        logger.info("Activando OCR Tesseract Fallback para Falabella...")
        ocr_text_list = []
        for i, img_b64 in enumerate(images):
            img_data = base64.b64decode(img_b64)
            img = Image.open(io.BytesIO(img_data))
            text_page = pytesseract.image_to_string(img, lang='spa')
            ocr_text_list.append(f"--- FALA PAG {i+1} ---\n{text_page}")
        pdf_text_content = "\n".join(ocr_text_list)

        # Pass 2: Transacciones
        all_transactions = []
        for i, img_b64 in enumerate(images):
            text_to_send = pdf_text_content if (i == 0 and len(pdf_text_content) > 50) else None
            logger.info(f"--- Falabella Pass 2 (Transacciones Pag {i+1}) ---")
            txs = self.ai_service.extract_transactions(img_b64, "Falabella", year_to_use, text_content=text_to_send)
            all_transactions.extend(txs)
            if text_to_send: break

        return {
            "transactions": all_transactions,
            "metadata": consolidated_metadata
        }

    def _parse_excel(self, file_content: bytes) -> Dict[str, Any]:
        """Lógica original para archivos Excel."""
        df = pd.read_excel(io.BytesIO(file_content))
        raw_transactions = []
        header_row = None
        for i, row in df.iterrows():
            if "Fecha" in row.values and "Descripción" in row.values:
                header_row = i
                break
        
        if header_row is not None:
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)
            for _, row in df.iterrows():
                if pd.isna(row["Fecha"]): continue
                raw_transactions.append({
                    "fecha": f"{datetime.now().year}-{str(row['Fecha'])}", # Simplificado para excel
                    "descripcion": str(row["Descripción"]),
                    "monto": float(str(row.get("Monto", 0)).replace('.','').replace(',','.')),
                    "tipo": "Gasto" if float(str(row.get("Monto", 0))) < 0 else "Ingreso"
                })

        return {
            "transactions": raw_transactions,
            "metadata": {"entidad": "Falabella (Excel)"}
        }

    def save_metadata(self, metadata: Dict[str, Any]):
        """Persiste metadatos en metadatos_documento."""
        if not metadata: return
        cursor = self.db.cursor()
        sql = """
            INSERT INTO metadatos_documento 
            (archivo_id, entidad_emisora, titular, identificador_cuenta, periodo_desde, periodo_hasta, atributos_adicionales)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        atributos_json = json.dumps(metadata.get("atributos_adicionales", {}))
        
        def fmt_date(d):
            if not d or d == "N/A": return None
            return d if "-" in d else None

        values = (
            self.archivo_id,
            "Falabella",
            metadata.get("titular"),
            metadata.get("cuenta"),
            fmt_date(metadata.get("periodo_desde")),
            fmt_date(metadata.get("periodo_hasta")),
            atributos_json
        )
        cursor.execute(sql, values)
        self.db.commit()
        cursor.close()

    def save_to_staging(self, data: Dict[str, Any]):
        """Guarda en staging_falabella con soporte para tipo_sugerido."""
        if "metadata" in data:
            self.save_metadata(data["metadata"])
            
        cursor = self.db.cursor()
        sql = """
            INSERT INTO staging_falabella 
            (archivo_id, fecha_texto, descripcion_cruda, tipo_sugerido, monto_pesos_crudo, cuotas, categoria_sugerida)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        for tx in data["transactions"]:
            cursor.execute(sql, (
                self.archivo_id, 
                tx.get("fecha"), 
                tx.get("descripcion"),
                tx.get("tipo", "Gasto"), # Captura el tipo de la IA
                str(tx.get("monto")),
                tx.get("cuotas", ""),
                tx.get("categoria", "Otros")
            ))
        self.db.commit()
        cursor.close()

    def consolidate(self):
        """Limpia y mueve a transacciones_consolidadas priorizando la IA y Motor Categorización."""
        from ..services.categorization import CategorizationService
        cat_service = CategorizationService(self.db)
        
        cursor = self.db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM staging_falabella WHERE archivo_id = %s", (self.archivo_id,))
        rows = cursor.fetchall()

        for row in rows:
            try:
                monto = abs(float(row["monto_pesos_crudo"]))
            except:
                monto = 0.0

            # Priorizar tipo sugerido por IA si existe, de lo contrario usar lógica de respaldo
            tipo = row.get("tipo_sugerido", "Gasto")
            
            cat_id = cat_service.categorizar(row["descripcion_cruda"], row.get("categoria_sugerida"))
            
            description = row["descripcion_cruda"].upper()
            tx_raw_string = f"{row['fecha_texto']}_{row['descripcion_cruda']}_{monto}_{self.archivo_id}"
            tx_id = hashlib.sha256(tx_raw_string.encode()).hexdigest()

            sql = """
                INSERT IGNORE INTO transacciones_consolidadas 
                (transaccion_id, archivo_id, fecha_transaccion, descripcion_limpia, monto, tipo, categoria_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                tx_id, 
                self.archivo_id, 
                row["fecha_texto"] if row["fecha_texto"] != "N/A" else datetime.now().date(), 
                row["descripcion_cruda"].strip(), 
                monto, 
                tipo,
                cat_id
            ))
        
        self.db.commit()
        cursor.close()
