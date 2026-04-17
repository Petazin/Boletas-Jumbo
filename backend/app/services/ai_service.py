import os
from openai import OpenAI
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # host.docker.internal permite acceder al host desde el contenedor Docker
        self.api_url = os.getenv("AI_API_URL", "http://host.docker.internal:1234/v1")
        self.client = OpenAI(base_url=self.api_url, api_key="not-needed")
        self.prompts_base_path = "/app/app/core/prompts"

    def _get_prompt(self, filename: str):
        path = os.path.join(self.prompts_base_path, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error leyendo el prompt {path}: {e}")
            return "Extrae la data solicitada de esta imagen."

    def extract_metadata(self, base64_image: str, origin: str):
        prompt_file = f"{origin.lower()}_metadata.txt"
        system_prompt = self._get_prompt(prompt_file)
        
        logger.info(f"Enviando Pass 1 (Metadata) usando {prompt_file}")
        
        try:
            response = self.client.chat.completions.create(
                model="local-model",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{system_prompt}\n\nProcesa la cabecera de este documento:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0,
                max_tokens=2048
            )
            
            content = response.choices[0].message.content
            logger.info("--- Pass 1 Result ---")
            logger.info(content)
            
            metadata = {
                "titular": "N/A",
                "cuenta": "N/A",
                "periodo_desde": "N/A",
                "periodo_hasta": "N/A",
                "atributos_adicionales": {}
            }
            current_mode = None
            
            for line in content.split("\n"):
                line = line.strip()
                if not line: continue
                
                if "[METADATA_START]" in line:
                    current_mode = "metadata"
                    continue
                if "[METADATA_END]" in line:
                    current_mode = None
                    continue
                
                if current_mode == "metadata":
                    if line.startswith("ATRIBUTOS:"):
                        try:
                            json_str = line.replace("ATRIBUTOS:", "").strip()
                            metadata["atributos_adicionales"] = json.loads(json_str)
                        except Exception as e:
                            logger.warning(f"Error parseando ATRIBUTOS JSON: {e}")
                    elif ":" in line:
                        key_raw, val = line.split(":", 1)
                        key = key_raw.strip().lower()
                        metadata[key] = val.strip()
                        
            return metadata
            
        except Exception as e:
            logger.error(f"Error crítico en IA Metadata (Pass 1): {str(e)}")
            return {}

    def extract_transactions(self, base64_image: str, origin: str, current_year: str = str(datetime.now().year), text_content: str = None):
        prompt_file = f"{origin.lower()}_transactions.txt"
        system_prompt = self._get_prompt(prompt_file)
        
        system_prompt = system_prompt.replace("{AÑO}", current_year)
        
        if text_content:
            logger.info(f"Enviando Pass 2 (Transactions TEXTO) usando {prompt_file} con AÑO {current_year}")
            logger.debug(f"Snippet de texto OCR: {text_content[:500]}...")
            messages = [
                {
                    "role": "user",
                    "content": f"{system_prompt}\n\nAQUÍ TIENES EL TEXTO EXTRAÍDO DEL DOCUMENTO:\n{text_content}"
                }
            ]
        else:
            logger.info(f"Enviando Pass 2 (Transactions IMAGEN) usando {prompt_file} con AÑO {current_year}")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{system_prompt}\n\nExtrae la tabla de este documento:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        
        try:
            response = self.client.chat.completions.create(
                model="local-model",
                messages=messages,
                temperature=0.0,
                max_tokens=2048
            )
            
            content = response.choices[0].message.content
            logger.info("--- Pass 2 Result ---")
            logger.info(content)
            
            transacciones = []
            current_mode = None
            
            for line in content.split("\n"):
                line = line.strip()
                if not line: continue
                
                if "[TABLE_START]" in line:
                    current_mode = "table"
                    continue
                if "[TABLE_END]" in line:
                    current_mode = None
                    continue
                
                if current_mode == "table":
                    if "|" in line and "DESC" not in line.upper(): 
                        try:
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 3:
                                monto_raw = parts[2]
                                monto_clean = monto_raw.replace(".", "").replace(",", ".")
                                monto_clean = re.sub(r'[^-0-9.]', '', monto_clean)
                                monto = float(monto_clean) if monto_clean else 0.0
                                
                                fecha_raw = parts[0]
                                fecha_iso = fecha_raw
                                
                                meses = {
                                    "ene": "01", "feb": "02", "mar": "03", "abr": "04", "may": "05", "jun": "06", 
                                    "jul": "07", "ago": "08", "sep": "09", "oct": "10", "nov": "11", "dic": "12"
                                }
                                
                                # Detección de formato ISO AAAA-MM-DD (nuevo estándar del prompt)
                                if re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_raw):
                                    fecha_iso = fecha_raw
                                elif "-" in fecha_raw:
                                    d_parts = [p.strip().lower() for p in fecha_raw.split("-")]
                                    if len(d_parts) >= 2:
                                        # Formato DD-MMM-AAAA o DD-MMM
                                        if len(d_parts[0]) <= 2:
                                            d = d_parts[0].zfill(2)
                                            m_text = d_parts[1][:3]
                                            m = meses.get(m_text, "01")
                                            fecha_iso = f"{current_year}-{m}-{d}"
                                        else:
                                            # Ya es AAAA-MM-DD (pero por si acaso re-validamos)
                                            fecha_iso = fecha_raw
                                elif "/" in fecha_raw:
                                    d_parts = fecha_raw.split("/")
                                    if len(d_parts) >= 2:
                                        d = d_parts[0].zfill(2)
                                        m = d_parts[1].zfill(2)
                                        y = d_parts[2] if len(d_parts) > 2 else current_year
                                        year = f"20{y}" if len(y) == 2 else y
                                        fecha_iso = f"{year}-{m}-{d}"

                                transacciones.append({
                                    "fecha": fecha_iso,
                                    "descripcion": parts[1],
                                    "monto": monto,
                                    "tipo": parts[3] if len(parts) > 3 else "Gasto",
                                    "categoria": parts[4] if len(parts) > 4 else "Otros"
                                })
                        except Exception as e:
                            logger.warning(f"Línea de tabla ignorada: {line} -> {e}")
            
            return transacciones
            
        except Exception as e:
            logger.error(f"Error crítico en IA Transactions (Pass 2): {str(e)}")
            return []
