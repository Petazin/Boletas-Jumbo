import logging
import os
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

def generate_standardized_filename(document_type: str, document_period: str, file_hash: str, original_filename: str) -> str:
    """
    Genera un nombre de archivo estandarizado basado en las convenciones del proyecto.

    Formato: [FechaProcesamiento]_[TipoDocumento]_[PeriodoDocumento]_[HashCorto].[Extension]
    """
    processing_date = datetime.now().strftime('%Y-%m-%d')
    short_hash = file_hash[:8]
    _, extension = os.path.splitext(original_filename)

    # Asegura que el período del documento esté en formato YYYY-MM
    period_formatted = document_period if document_period else "SIN_FECHA"
    try:
        # Intenta convertir si viene como objeto de fecha o fecha completa
        if isinstance(document_period, datetime):
            period_formatted = document_period.strftime('%Y-%m')
        else:
            # Si es un string, intenta parsearlo por si viene como YYYY-MM-DD
            period_formatted = datetime.strptime(document_period, '%Y-%m-%d').strftime('%Y-%m')
    except (ValueError, TypeError):
        # Si falla, se asume que ya está en formato YYYY-MM o es inválido
        pass

    filename = f"{processing_date}_{document_type}_{period_formatted}_{short_hash}{extension}"
    return filename