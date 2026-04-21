import logging

logger = logging.getLogger(__name__)

class CategorizationService:
    def __init__(self, db_conn):
        self.db = db_conn
        self.reglas = self._cargar_reglas()
        self.categorias_ia_map = self._cargar_categorias_map()

    def _cargar_reglas(self):
        logger.info("Cargando reglas de categorización desde DB...")
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("SELECT patron, categoria_id FROM reglas_categorizacion")
            reglas = cursor.fetchall()
            cursor.close()
            return reglas
        except Exception as e:
            logger.error(f"Error cargando reglas: {e}")
            return []

    def _cargar_categorias_map(self):
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("SELECT categoria_id, nombre FROM categorias_principales")
            cats = cursor.fetchall()
            cursor.close()
            
            cmap = {}
            for c in cats:
                nombre = c["nombre"].lower()
                cmap[nombre] = c["categoria_id"]
                if "/" in nombre:
                    for part in nombre.split("/"):
                        cmap[part.strip()] = c["categoria_id"]
            return cmap
        except Exception as e:
            logger.error(f"Error cargando mapa de categorías: {e}")
            return {}

    def categorizar(self, descripcion_limpia: str, categoria_sugerida_ia: str = None) -> int:
        desc_upper = descripcion_limpia.upper()
        
        # 1. Match local rules (Substring rápido)
        for regla in self.reglas:
            if regla["patron"].upper() in desc_upper:
                return regla["categoria_id"]
        
        # 2. Fallback to IA Suggestion
        if categoria_sugerida_ia:
            cat_ia_clean = categoria_sugerida_ia.strip().lower()
            
            # Direct match
            if cat_ia_clean in self.categorias_ia_map:
                return self.categorias_ia_map[cat_ia_clean]
            
            # Partial match (e.g. 'Salud' in 'salud y bienestar')
            for db_cat_name, cat_id in self.categorias_ia_map.items():
                if cat_ia_clean in db_cat_name or db_cat_name in cat_ia_clean:
                    return cat_id

        # 3. Fallback to "Otros" (ID: 8)
        return 8
