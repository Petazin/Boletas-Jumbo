from database_utils import db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_transactions_pago_tef():
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            description_to_check = 'Pago Pesos TEF'
            query = "SELECT COUNT(*) FROM transacciones_tarjeta_credito_raw WHERE descripcion_transaccion = %s"
            cursor.execute(query, (description_to_check,))
            result = cursor.fetchone()
            
            logging.info(f'Count for "{description_to_check}": {result[0]}')
            
            if result[0] > 0:
                query_select = "SELECT fecha_cargo_original, descripcion_transaccion, cargos_pesos, abonos_pesos FROM transacciones_tarjeta_credito_raw WHERE descripcion_transaccion = %s LIMIT 10"
                cursor.execute(query_select, (description_to_check,))
                records = cursor.fetchall()
                logging.info(f'Sample records for "{description_to_check}":')
                for record in records:
                    logging.info(record)

            cursor.close()
    except Exception as e:
        logging.error(f'Error al consultar la base de datos: {e}')

if __name__ == '__main__':
    check_transactions_pago_tef()