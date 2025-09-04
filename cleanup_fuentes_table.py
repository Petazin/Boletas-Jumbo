import logging
from database_utils import db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cleanup_fuentes_table():
    """
    Limpia y reestructura la tabla `fuentes` añadiendo la columna `ambito`
    y normalizando los datos existentes.
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Añadir la columna 'ambito' si no existe
            logging.info("Verificando si la columna 'ambito' existe...")
            cursor.execute("SHOW COLUMNS FROM fuentes LIKE 'ambito'")
            if not cursor.fetchone():
                logging.info("Añadiendo columna 'ambito' a la tabla 'fuentes'...")
                cursor.execute("ALTER TABLE fuentes ADD COLUMN ambito VARCHAR(50) DEFAULT 'Nacional' AFTER tipo_fuente")
                logging.info("Columna 'ambito' añadida con éxito.")
            else:
                logging.info("La columna 'ambito' ya existe.")

            # 2. Definir las correcciones a aplicar
            corrections = [
                # id=1: Banco de Chile, tipo=Cuenta Corriente, ambito=Nacional
                "UPDATE fuentes SET nombre_fuente = 'Banco de Chile - Cuenta Corriente', tipo_fuente = 'Cuenta Corriente', ambito = 'Nacional' WHERE fuente_id = 1;",
                # id=2: Banco Falabella, tipo=Cuenta Corriente, ambito=Nacional
                "UPDATE fuentes SET tipo_fuente = 'Cuenta Corriente', ambito = 'Nacional' WHERE fuente_id = 2;",
                # id=3: Banco de Chile, tipo=Tarjeta Credito, ambito=Nacional
                "UPDATE fuentes SET tipo_fuente = 'Tarjeta Credito', ambito = 'Nacional' WHERE fuente_id = 3;",
                # id=4: Banco de Chile, tipo=Tarjeta Credito, ambito=Internacional
                "UPDATE fuentes SET tipo_fuente = 'Tarjeta Credito', ambito = 'Internacional' WHERE fuente_id = 4;",
                # id=5: Banco Falabella, tipo=Línea de Crédito, ambito=Nacional
                "UPDATE fuentes SET tipo_fuente = 'Línea de Crédito', ambito = 'Nacional' WHERE fuente_id = 5;",
                # id=6: Banco Falabella, tipo=Tarjeta Credito, ambito = 'Nacional'
                "UPDATE fuentes SET tipo_fuente = 'Tarjeta Credito', ambito = 'Nacional' WHERE fuente_id = 6;"
            ]
            
            # 3. Aplicar las correcciones
            logging.info("Aplicando correcciones a los datos de la tabla 'fuentes'...")
            for query in corrections:
                cursor.execute(query)
                logging.info(f"Ejecutado: {query.strip()}")
            
            conn.commit()
            cursor.close()
            logging.info("¡La tabla 'fuentes' ha sido limpiada y actualizada exitosamente!")

    except Exception as e:
        logging.error(f"Ocurrió un error durante la limpieza de la tabla 'fuentes': {e}")

if __name__ == '__main__':
    cleanup_fuentes_table()