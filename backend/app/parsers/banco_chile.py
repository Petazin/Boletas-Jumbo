import pdfplumber
import re
import io
import json
import logging
import hashlib
import base64
from typing import Dict, Any
from ..core.base_parser import BaseParser
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

class BancoChileParser(BaseParser):
    def parse(self, file_content: bytes, password: str = None) -> Dict[str, Any]:
        """Extrae datos usando la estrategia Two-Pass IA Vision con soporte de password."""
        from ..core.image_utils import pdf_to_base64_images
        
        logger.info(f"Iniciando procesamiento Two-Pass para archivo_id: {self.archivo_id}")
        
        # Pasar la contraseña a la conversión visual
        images = pdf_to_base64_images(file_content, password=password)
        if not images:
            raise ValueError("No se pudieron extraer imágenes del PDF del Banco de Chile.")
            
        all_transactions = []
        
        # Pass 1: Metadatos
        logger.info("--- Banco Chile Pass 1 (Metadata) ---")
        consolidated_metadata = self.ai_service.extract_metadata(images[0], "Banco_Chile")
        
        from datetime import datetime
        year_to_use = str(datetime.now().year)
        
        if consolidated_metadata:
            p_desde = consolidated_metadata.get("periodo_desde", "")
            if p_desde and "/" in p_desde:
                parts = p_desde.split("/")
                if len(parts) >= 3:
                    y = parts[2]
                    year_to_use = f"20{y}" if len(y) == 2 else y
        
        # Extracción de texto digital (opcional, pdfplumber puede fallar con clave)
        pdf_text_content = ""
        try:
            # Nota: para pdfplumber también podríamos pasar la contraseña si fuera necesario
            with pdfplumber.open(io.BytesIO(file_content), password=password) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pdf_text_content += text + "\n"
        except Exception as e:
            logger.warning(f"No se pudo extraer texto nativo con pdfplumber: {e}")
            
        # Fallback a OCR
        if len(pdf_text_content.strip()) < 100:
            logger.info("Texto nativo insuficiente. Iniciando OCR Tesseract Fallback...")
            ocr_text_list = []
            for i, img_b64 in enumerate(images):
                try:
                    img_data = base64.b64decode(img_b64)
                    img = Image.open(io.BytesIO(img_data))
                    text_page = pytesseract.image_to_string(img, lang='spa')
                    ocr_text_list.append(f"--- PAGINA {i+1} ---\n{text_page}")
                except Exception as e:
                    logger.error(f"Error en OCR Pag {i+1}: {e}")
            pdf_text_content = "\n".join(ocr_text_list)
            
        # Pass 2: Transacciones
        for i, img_b64 in enumerate(images):
            text_to_send = pdf_text_content if (i == 0 and len(pdf_text_content) > 50) else None
            logger.info(f"--- Banco Chile Pass 2 (Transacciones Pag {i+1}) ---")
            txs = self.ai_service.extract_transactions(img_b64, "Banco_Chile", year_to_use, text_content=text_to_send)
            all_transactions.extend(txs)
            if text_to_send: break
            
        return {
            "transactions": all_transactions,
            "metadata": consolidated_metadata
        }

    def save_metadata(self, metadata: Dict[str, Any]):
        """Persiste la información de cabecera en metadatos_documento."""
        if not metadata: return
        cursor = self.db.cursor()
        
        def parse_date(date_str):
            if not date_str or date_str == "N/A": return None
            try:
                if "/" in date_str:
                    d, m, y = date_str.split("/")
                    year = f"20{y}" if len(y) == 2 else y
                    return f"{year}-{m.zfill(2)}-{d.zfill(2)}"
                return date_str
            except: return None

        sql = """
            INSERT INTO metadatos_documento 
            (archivo_id, entidad_emisora, titular, identificador_cuenta, periodo_desde, periodo_hasta, atributos_adicionales)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        atributos_json = json.dumps(metadata.get("atributos_adicionales", {}))
        values = (
            self.archivo_id,
            "Banco de Chile",
            metadata.get("titular"),
            metadata.get("cuenta"),
            parse_date(metadata.get("periodo_desde")),
            parse_date(metadata.get("periodo_hasta")),
            atributos_json
        )
        cursor.execute(sql, values)
        self.db.commit()
        cursor.close()

    def save_to_staging(self, data: Dict[str, Any]):
        """Guarda en staging_banco_chile."""
        if "metadata" in data:
            self.save_metadata(data["metadata"])
            
        if not data.get("transactions"):
            logger.warning("No se encontraron transacciones devueltas por la IA. El documento podría estar vacío de movimientos (típico en LC).")
            return

            
        cursor = self.db.cursor()
        sql = """
            INSERT INTO staging_banco_chile 
            (archivo_id, fecha_texto, descripcion_cruda, monto_cheques_cargos, monto_depositos_abonos, categoria_sugerida)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        for tx in data["transactions"]:
            monto = tx.get("monto", 0)
            es_gasto = tx.get("tipo") == "Gasto"
            values = (
                self.archivo_id, 
                tx.get("fecha"), 
                tx.get("descripcion"), 
                str(monto) if es_gasto else "0",
                str(monto) if not es_gasto else "0",
                tx.get("categoria", "Otros")
            )
            cursor.execute(sql, values)
            
        self.db.commit()
        cursor.close()

    def consolidate(self):
        """Mueve a transacciones_consolidadas pasándolas por el motor de categorización híbrido."""
        from ..services.categorization import CategorizationService
        cat_service = CategorizationService(self.db)
        
        cursor = self.db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM staging_banco_chile WHERE archivo_id = %s", (self.archivo_id,))
        rows = cursor.fetchall()

        for row in rows:
            cargo = float(row["monto_cheques_cargos"]) if row["monto_cheques_cargos"] else 0.0
            abono = float(row["monto_depositos_abonos"]) if row["monto_depositos_abonos"] else 0.0
            monto = cargo if cargo > 0 else abono
            tipo = "Gasto" if cargo > 0 else "Ingreso"
            
            # Bloqueo de saldos falsamente catalogados
            desc_upper = row["descripcion_cruda"].upper()
            if any(term in desc_upper for term in ["SALDO INICIAL", "SALDO FINAL", "SALDO TOTAL", "CUPO LINEA DE CREDITO"]):
                logger.info(f"Omitiendo fila de balance detectada erróneamente: {row['descripcion_cruda']}")
                continue
            
            # Hybrid categorization
            cat_id = cat_service.categorizar(row["descripcion_cruda"], row.get("categoria_sugerida"))
            
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
                row["fecha_texto"], 
                row["descripcion_cruda"].strip(), 
                monto, 
                tipo,
                cat_id
            ))
        self.db.commit()
        cursor.close()
