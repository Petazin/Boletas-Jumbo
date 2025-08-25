import os
import logging
from bank_ingestion import parse_bank_account_statement_xls

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ingest_all_bank_statements(base_dir):
    """
    Recorre el directorio base y sus subdirectorios para encontrar archivos XLS
    de extractos bancarios e inicia su procesamiento.
    """
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.xls'):
                file_path = os.path.join(root, file)
                logging.info(f"Procesando archivo: {file_path}")

                # Determinar source_name y source_type basado en la ruta del archivo
                # Esto es una heurística simple y puede necesitar ser más sofisticada
                # en un sistema de producción.
                relative_path = os.path.relpath(file_path, base_dir)
                path_parts = relative_path.split(os.sep)

                source_name = "Desconocido"
                source_type = "Banco" # Por defecto para archivos en descargas/Banco

                if len(path_parts) >= 2:
                    # Ejemplo: descargas/Banco/banco de chile/cuenta corriente/cartola.xls
                    # path_parts[0] = "banco de chile"
                    # path_parts[1] = "cuenta corriente"
                    bank_name = path_parts[0]
                    account_type = path_parts[1] if len(path_parts) > 1 else ""

                    if "tarjeta de credito" in account_type.lower():
                        source_type = "Tarjeta de Credito"
                        source_name = f"{bank_name} - {account_type.replace('tarjeta de credito', 'Tarjeta de Crédito').title()}"
                    elif "cuenta corriente" in account_type.lower():
                        source_type = "Banco"
                        source_name = f"{bank_name} - {account_type.replace('cuenta corriente', 'Cuenta Corriente').title()}"
                    elif "linea de credito" in account_type.lower():
                        source_type = "Banco"
                        source_name = f"{bank_name} - {account_type.replace('linea de credito', 'Línea de Crédito').title()}"
                    else:
                        source_name = f"{bank_name} - {account_type.title()}"
                else:
                    source_name = os.path.basename(root) # Fallback a nombre del directorio

                logging.info(f"Detectado source_name: {source_name}, source_type: {source_type}")

                try:
                    parse_bank_account_statement_xls(file_path, source_name, source_type)
                except Exception as e:
                    logging.error(f"Error al procesar {file_path}: {e}")

if __name__ == "__main__":
    # Ruta base donde se encuentran las descargas de bancos
    # Asegúrate de que esta ruta sea correcta en tu sistema
    base_download_dir = r"c:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco"
    ingest_all_bank_statements(base_download_dir)
