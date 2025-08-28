import pdfplumber
import pandas as pd
import os
import logging
import hashlib
import shutil
from database_utils import db_connection
from collections import defaultdict
from config import PROCESSED_BANK_STATEMENTS_DIR

# Configuración de logging para dar seguimiento a la ejecución del script.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_file_hash(file_path):
    """
    Calcula el hash SHA-256 de un archivo para generar una huella digital única.
    Esto es crucial para identificar un archivo por su contenido y no por su nombre o ruta,
    evitando así procesar duplicados.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Se lee el archivo en bloques de 4KB para no sobrecargar la memoria,
        # especialmente si se procesaran archivos muy grandes.
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_all_pdf_files(directory):
    """Encuentra todos los archivos PDF en un directorio y los devuelve en una lista."""
    pdf_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, filename))
    return pdf_files

def is_file_processed(conn, file_hash):
    """Verifica en la BD si un archivo con un hash específico ya ha sido procesado."""
    # Se usa un cursor bufferizado para asegurar que todos los resultados se traen del servidor
    # de inmediato, evitando errores de 'Unread result' al cerrar la conexión.
    cursor = conn.cursor(buffered=True)
    query = "SELECT 1 FROM metadatos_cartolas_bancarias_raw WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone() is not None
    cursor.close()
    return result

def get_source_id(conn, source_name='Banco de Chile'):
    """Obtiene el ID de la fuente 'Banco de Chile', creándolo si no existe."""
    cursor = conn.cursor(buffered=True)
    query = "SELECT fuente_id FROM fuentes WHERE nombre_fuente = %s"
    cursor.execute(query, (source_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        insert_query = "INSERT INTO fuentes (nombre_fuente) VALUES (%s)"
        cursor.execute(insert_query, (source_name,))
        conn.commit()
        return cursor.lastrowid

def insert_metadata(conn, source_id, pdf_path, file_hash):
    """Inserta los metadatos del archivo (incluyendo su hash) en la base de datos."""
    cursor = conn.cursor()
    query = """
    INSERT INTO metadatos_cartolas_bancarias_raw (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    values = (source_id, pdf_path, file_hash, 'Bank Statement')
    cursor.execute(query, values)
    conn.commit()
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte un string monetario a un número de punto flotante (float)."""
    if isinstance(value, str):
        value = value.replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if value is not None else 0.0

def group_words_by_line(words, tolerance=3):
    """
    Agrupa las palabras extraídas del PDF en líneas coherentes.
    El problema principal con los PDFs es que lo que visualmente parece una línea
    no siempre tiene la misma coordenada vertical (top) para todas sus palabras.
    Esta función soluciona eso agrupando palabras que están verticalmente
    'suficientemente cerca' (definido por la tolerancia).
    """
    if not words:
        return []
    # Se agrupan las palabras por su coordenada 'top' usando un diccionario.
    # La clave del diccionario es la coordenada vertical de la línea.
    lines = defaultdict(list)
    # Se ordenan las palabras por su posición vertical para procesarlas en orden.
    sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
    
    # Se toma la posición de la primera palabra como el ancla para la primera línea.
    current_line_top = sorted_words[0]['top']
    for word in sorted_words:
        # Si la palabra actual está dentro de la tolerancia vertical de la línea que se está formando,
        # se considera parte de la misma línea.
        if abs(word['top'] - current_line_top) <= tolerance:
            lines[current_line_top].append(word)
        # Si la palabra está fuera de la tolerancia, se asume que es el comienzo de una nueva línea.
        else:
            current_line_top = word['top']
            lines[current_line_top].append(word)
            
    # Finalmente, se devuelve una lista de líneas, donde cada línea es una lista de palabras ordenadas horizontalmente.
    return [sorted(line, key=lambda w: w['x0']) for top, line in sorted(lines.items())]

def parse_bank_statement_pdf(pdf_path):
    """Función principal de parseo que orquesta la extracción de datos del PDF."""
    logging.info(f"Iniciando parseo de: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        # Se definen las coordenadas horizontales (eje X) que delimitan cada columna.
        # Estos valores se ajustaron manualmente observando la estructura del PDF para asegurar precisión.
        column_boundaries = [15, 50, 230, 300, 380, 450, 550]
        headers = ['FECHA DIA/MES', 'DETALLE DE TRANSACCION', 'SUCURSAL', 'N° DOCTO', 'MONTO CHEQUES O CARGOS', 'MONTO DEPOSITOS O ABONOS', 'SALDO']
        
        # Se recorta la página para aislar únicamente la tabla de transacciones,
        # ignorando cabeceras y pies de página que confundían al extractor.
        y0, y1 = 0, page.height
        try:
            header_text = page.search("DETALLE DE TRANSACCION")
            if header_text:
                y0 = header_text[0]['top'] + 10
            footer_text = page.search("RETENCION A 1 DIA")
            if footer_text:
                y1 = footer_text[0]['top'] - 5
        except Exception:
            pass
        bbox = (0, y0, page.width, y1)
        cropped_page = page.crop(bbox)
        
        # Se extraen todas las palabras del área recortada.
        words = cropped_page.extract_words(x_tolerance=2, y_tolerance=2)
        
        # Se utiliza la función de agrupación para reconstruir las líneas de la tabla.
        lines = group_words_by_line(words)
        
        # Se itera sobre cada línea reconstruida para asignar las palabras a las columnas correctas.
        table_data = []
        # Se omite la primera línea (lines[1:]) porque es la cabecera de la tabla, no una transacción.
        for line_words in lines[1:]:
            row = ['' for _ in headers]
            for word in line_words:
                for i, x_start in enumerate(column_boundaries):
                    x_end = column_boundaries[i+1] if i + 1 < len(column_boundaries) else page.width
                    if x_start <= word['x0'] < x_end:
                        row[i] = (row[i] + ' ' + word['text']).strip()
                        break
            # Se aplica un filtro para asegurar que solo las filas que contienen una fecha (con '/') se procesen.
            if row[0] and '/' in row[0]:
                table_data.append(row)
        
        if not table_data:
            logging.error(f"No se pudieron extraer datos de transacciones de {pdf_path}")
            return None
        
        # Se crea el DataFrame de pandas con los datos limpios.
        df = pd.DataFrame(table_data, columns=headers)
        logging.info(f"DataFrame construido con éxito para {pdf_path}")
        
        # Se renombran las columnas para que coincidan con la base de datos.
        column_mapping = {
            'FECHA DIA/MES': 'fecha_transaccion_str',
            'DETALLE DE TRANSACCION': 'descripcion_transaccion',
            'SUCURSAL': 'canal_o_sucursal',
            'N° DOCTO': 'doc_number',
            'MONTO CHEQUES O CARGOS': 'cargos_pesos',
            'MONTO DEPOSITOS O ABONOS': 'abonos_pesos',
            'SALDO': 'saldo_pesos'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Se limpian y convierten los valores numéricos.
        for col in ['cargos_pesos', 'abonos_pesos', 'saldo_pesos']:
            if col in df.columns:
                df[col] = df[col].apply(parse_and_clean_value)
        
        final_columns = [col for col in column_mapping.values() if col in df.columns]
        return df[final_columns]

def insert_transactions(conn, metadata_id, source_id, transactions_df):
    """Inserta el DataFrame de transacciones en la base de datos."""
    cursor = conn.cursor()
    query = """
    INSERT INTO transacciones_cuenta_bancaria_raw (
        metadata_id, fuente_id, fecha_transaccion_str, descripcion_transaccion, 
        canal_o_sucursal, cargos_pesos, abonos_pesos, saldo_pesos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    for _, row in transactions_df.iterrows():
        values = (
            metadata_id,
            source_id,
            row.get('fecha_transaccion_str'),
            row.get('descripcion_transaccion'),
            row.get('canal_o_sucursal'),
            row.get('cargos_pesos'),
            row.get('abonos_pesos'),
            row.get('saldo_pesos')
        )
        cursor.execute(query, values)
    conn.commit()
    logging.info(f"Se insertaron {len(transactions_df)} transacciones para metadata_id: {metadata_id}")

def main():
    """Función principal que orquesta todo el proceso."""
    pdf_directory = r'c:\Users\Petazo\Desktop\Boletas Jumbo\descargas\Banco\banco de chile\cuenta corriente'
    pdf_files = find_all_pdf_files(pdf_directory)
    
    if not pdf_files:
        logging.info(f"No se encontraron archivos PDF en: {pdf_directory}")
        return

    logging.info(f"Se encontraron {len(pdf_files)} archivos PDF.")

    with db_connection() as conn:
        for pdf_path in pdf_files:
            try:
                file_hash = calculate_file_hash(pdf_path)
                if is_file_processed(conn, file_hash):
                    logging.info(f"Archivo ya procesado (hash existente), omitiendo: {os.path.basename(pdf_path)}")
                    continue

                transactions_df = parse_bank_statement_pdf(pdf_path)
                if transactions_df is None or transactions_df.empty:
                    continue

                source_id = get_source_id(conn)
                metadata_id = insert_metadata(conn, source_id, pdf_path, file_hash)
                insert_transactions(conn, metadata_id, source_id, transactions_df)
                
                # Mover el archivo PDF procesado a la carpeta de archivos procesados
                processed_filepath = os.path.join(PROCESSED_BANK_STATEMENTS_DIR, os.path.basename(pdf_path))
                os.makedirs(os.path.dirname(processed_filepath), exist_ok=True)
                shutil.move(pdf_path, processed_filepath)
                logging.info(f"Archivo movido a la carpeta de procesados: {processed_filepath}")

                logging.info(f"Proceso de ingesta completado con éxito para: {os.path.basename(pdf_path)}")

            except Exception as e:
                logging.error(f"Ocurrió un error procesando el archivo {os.path.basename(pdf_path)}: {e}")

if __name__ == '__main__':
    main()