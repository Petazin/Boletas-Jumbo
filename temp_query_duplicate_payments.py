from database_utils import db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def query_duplicate_payments():
    """Consulta registros de 'Pago Dolar TEF' para fuente_id=4 en enero 2025."""
    try:
        with db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT 
                fecha_cargo_original, 
                descripcion_transaccion, 
                cargos_pesos, 
                abonos_pesos, 
                monto_usd, 
                tipo_cambio, 
                metadata_id
            FROM 
                transacciones_tarjeta_credito_raw 
            WHERE 
                fuente_id = 4 
                AND descripcion_transaccion = 'Pago Dolar TEF' 
                AND fecha_cargo_original LIKE '2025-01%';
            """
            cursor.execute(query)
            records = cursor.fetchall()
            
            if not records:
                logging.info("No se encontraron registros de 'Pago Dolar TEF' para fuente_id=4 en enero 2025.")
                return

            logging.info(f"Se encontraron {len(records)} registros de 'Pago Dolar TEF':")
            for record in records:
                logging.info(record)

            cursor.close()
    except Exception as e:
        logging.error(f'Error al consultar la base de datos: {e}')

if __name__ == '__main__':
    query_duplicate_payments()
