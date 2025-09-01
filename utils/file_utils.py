import logging
from datetime import datetime

# Configuración del logger para movimientos de archivos
file_movement_logger = logging.getLogger('file_movements')
file_movement_logger.setLevel(logging.INFO)

# Crear un handler para escribir en un archivo
log_file_path = 'file_movements.log'
file_handler = logging.FileHandler(log_file_path)

# Formato del log
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)

# Añadir el handler al logger
file_movement_logger.addHandler(file_handler)

def log_file_movement(original_path, destination_path, status="SUCCESS", message=""):
    """
    Registra un movimiento de archivo en un log centralizado.

    Args:
        original_path (str): Ruta original del archivo.
        destination_path (str): Ruta de destino del archivo.
        status (str): Estado del movimiento (ej. "SUCCESS", "FAILED").
        message (str): Mensaje adicional sobre el movimiento.
    """
    log_message = f"ORIGEN: {original_path} | DESTINO: {destination_path} | ESTADO: {status} | MENSAJE: {message}"
    file_movement_logger.info(log_message)
