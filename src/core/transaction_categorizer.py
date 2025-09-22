# -*- coding: utf-8 -*-
"""
Motor de Clasificación de Transacciones

Este módulo proporciona la lógica para categorizar una transacción financiera 
basada en su descripción, utilizando un conjunto de reglas predefinidas en la 
base de datos.
"""

import sys
import os
import logging

# Añadir el directorio raíz del proyecto al sys.path para resolver importaciones
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from db.database_utils import db_connection

class TransactionCategorizer:
    """
    Clase que encapsula la lógica para categorizar transacciones.

    Al inicializarse, carga las reglas de clasificación desde la base de datos 
    para optimizar el rendimiento, evitando consultas repetitivas a la BD.
    """
    def __init__(self):
        """
        Inicializa el categorizador cargando las reglas y la categoría por 
        defecto desde la base de datos.
        """
        self.rules = []
        self.default_subcategory_id = None
        self._load_rules()

    def _load_rules(self):
        """
        Carga las reglas de mapeo y la subcategoría por defecto desde la BD.
        Las reglas se ordenan por prioridad y luego por longitud de la palabra 
        clave para que las reglas más específicas se evalúen primero.
        """
        logging.info("Cargando reglas de clasificación de transacciones...")
        try:
            with db_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # Cargar todas las reglas, ordenadas por prioridad y especificidad
                sql_rules = """
                    SELECT palabra_clave, subcategoria_id
                    FROM mapeo_clasificacion_transacciones
                    ORDER BY prioridad DESC, LENGTH(palabra_clave) DESC
                """
                cursor.execute(sql_rules)
                self.rules = cursor.fetchall()

                # Cargar la subcategoría por defecto ('Otros Gastos')
                sql_default = """
                    SELECT subcategoria_id 
                    FROM subcategorias 
                    WHERE nombre_subcategoria = 'Otros Gastos' LIMIT 1
                """
                cursor.execute(sql_default)
                result = cursor.fetchone()
                if result:
                    self.default_subcategory_id = result['subcategoria_id']
                else:
                    logging.error("No se pudo encontrar la subcategoría por defecto 'Otros Gastos'.")

                logging.info(f"{len(self.rules)} reglas cargadas. ID por defecto: {self.default_subcategory_id}")

        except Exception as e:
            logging.error(f"Error al cargar las reglas de clasificación: {e}")
            self.rules = [] # Asegurar que las reglas estén vacías en caso de error

    def categorize(self, description: str) -> int | None:
        """
        Categoriza una transacción basada en su descripción.

        Args:
            description: La descripción de la transacción a categorizar.

        Returns:
            El ID de la subcategoría correspondiente, o el ID de la subcategoría 
            por defecto si no se encuentra ninguna coincidencia.
        """
        if not isinstance(description, str) or not self.rules:
            return self.default_subcategory_id

        # Convertir a minúsculas para una comparación insensible a mayúsculas/minúsculas
        description_lower = description.lower()

        for rule in self.rules:
            keyword = rule['palabra_clave'].lower()
            
            # Por ahora, se asume la lógica 'contiene'.
            # La DB soporta 'exacto', 'empieza_con', etc. para futuras mejoras.
            if keyword in description_lower:
                # Devolver el ID de la subcategoría al encontrar la primera coincidencia
                # gracias al ordenamiento por prioridad y longitud.
                return rule['subcategoria_id']

        # Si el bucle termina sin encontrar coincidencias, devolver el ID por defecto.
        return self.default_subcategory_id

# ==============================================================================
# EJEMPLO DE USO (PARA PRUEBAS)
# ==============================================================================
if __name__ == '__main__':
    # Configuración básica de logging para ver la salida de la clase
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("---""Inicializando el categorizador""---")
    categorizer = TransactionCategorizer()

    # Solo proceder si las reglas se cargaron correctamente
    if categorizer.rules:
        print("\n---""Probando con descripciones de ejemplo""---")
        test_descriptions = [
            "COMPRA EN JUMBO EL BELLOTO",
            "PAGO AUTOM. LINEA DE CREDITO",
            "Transferencia de Terceros a mi cuenta",
            "Pago de mi tarjeta NETFLIX.COM",
            "Un gasto completamente desconocido",
            "COMPRA MERPAGO*PANADERIA VILL"
        ]

        for desc in test_descriptions:
            cat_id = categorizer.categorize(desc)
            print(f"Descripción: '{desc}' -> Subcategoría ID: {cat_id}")
    else:
        print("\nNo se pudieron cargar las reglas. La prueba no puede continuar.")
