import pdfplumber
import pandas as pd
import os
import logging
import hashlib
import shutil
from utils.file_utils import log_file_movement
from database_utils import db_connection
from collections import defaultdict


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_all_pdf_files(directory):
    pdf_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(directory, filename))
    return pdf_files

def is_file_processed(conn, file_hash):
    cursor = conn.cursor(buffered=True)
    query = "SELECT 1 FROM metadatos_cartolas_bancarias_raw WHERE file_hash = %s"
    cursor.execute(query, (file_hash,))
    result = cursor.fetchone() is not None
    cursor.close()
    return result

def get_source_id(conn, source_name='Banco de Chile'):
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
    cursor = conn.cursor()
    query = """
    INSERT INTO metadatos_cartolas_bancarias_raw (fuente_id, nombre_archivo_original, file_hash, document_type)
    VALUES (%s, %s, %s, %s)
    """
    # Usamos os.path.basename para ser consistentes
    values = (source_id, os.path.basename(pdf_path), file_hash, 'Bank Statement')
    cursor.execute(query, values)
    conn.commit()
    return cursor.lastrowid

def parse_and_clean_value(value):
    """Limpia y convierte un string monetario a un número de punto flotante (float)."""
    if isinstance(value, str):
        # --- INICIO DE LA CORRECCIÓN ---
        # Si el valor contiene espacios, es probable que sea un error de extracción del PDF.
        # Nos quedamos con la primera parte, que suele ser el monto correcto.
        if ' ' in value:
            value = value.split(' ')[0]
        # --- FIN DE LA CORRECCIÓN ---
        
        value = value.replace('.', '').replace(',', '.')
        return float(value) if value and value != '-' else 0.0
    return value if pd.notna(value) else 0.0

def group_words_by_line(words, tolerance=3):
    if not words:
        return []
    lines = defaultdict(list)
    sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
    
    current_line_top = sorted_words[0]['top']
    for word in sorted_words:
        if abs(word['top'] - current_line_top) <= tolerance:
            lines[current_line_top].append(word)
        else:
            current_line_top = word['top']
            lines[current_line_top].append(word)
            
    return [sorted(line, key=lambda w: w['x0']) for top, line in sorted(lines.items())]

def parse_bank_statement_pdf(pdf_path):
    logging.info(f"Iniciando parseo de: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        column_boundaries = [15, 50, 230, 300, 380, 450, 550]
        headers = ['FECHA DIA/MES', 'DETALLE DE TRANSACCION', 'SUCURSAL', 'N° DOCTO', 'MONTO CHEQUES O CARGOS', 'MONTO DEPOSITOS O ABONOS', 'SALDO']
        
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
        
        words = cropped_page.extract_words(x_tolerance=2, y_tolerance=2)
        lines = group_words_by_line(words)
        
        table_data = []
        for line_words in lines[1:]:
            row = ['' for _ in headers]
            for word in line_words:
                for i, x_start in enumerate(column_boundaries):
                    x_end = column_boundaries[i+1] if i + 1 < len(column_boundaries) else page.width
                    if x_start <= word['x0'] < x_end:
                        row[i] = (row[i] + ' ' + word['text']).strip()
                        break
            if row[0] and '/' in row[0]:
                table_data.append(row)
        
        if not table_data:
            logging.error(f"No se pudieron extraer datos de transacciones de {pdf_path}")
            return None
        
        df = pd.DataFrame(table_data, columns=headers)
        logging.info(f"DataFrame construido con éxito para {pdf_path}")
        
        column_mapping = {
            'FECHA DIA/MES': 'fecha_transaccion_str', 'DETALLE DE TRANSACCION': 'descripcion_transaccion',
            'SUCURSAL': 'canal_o_sucursal', 'N° DOCTO': 'doc_number',
            'MONTO CHEQUES O CARGOS': 'cargos_pesos', 'MONTO DEPOSITOS O ABONOS': 'abonos_pesos',
            'SALDO': 'saldo_pesos'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        for col in ['cargos_pesos', 'abonos_pesos', 'saldo_pesos']:
            if col in df.columns:
                df[col] = df[col].apply(parse_and_clean_value)
        
        # Reemplazar NaN con None para compatibilidad con la BD
        df = df.astype(object).where(pd.notnull(df), None)
        
        final_columns = [col for col in column_mapping.values() if col in df.columns]
        return df[final_columns]

def insert_transactions(conn, metadata_id, source_id, transactions_df):
    cursor = conn.cursor()
    query = """
    INSERT INTO transacciones_cuenta_bancaria_raw (
        metadata_id, fuente_id, fecha_transaccion_str, descripcion_transaccion, 
        canal_o_sucursal, cargos_pesos, abonos_pesos, saldo_pesos
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    for _, row in transactions_df.iterrows():
        values = (
            metadata_id, source_id, row.get('fecha_transaccion_str'),
            row.get('descripcion_transaccion'), row.get('canal_o_sucursal'),
            row.get('cargos_pesos'), row.get('abonos_pesos'), row.get('saldo_pesos')
        )
        cursor.execute(query, values)
    conn.commit()
    logging.info(f"Se insertaron {len(transactions_df)} transacciones para metadata_id: {metadata_id}")

def main():
    pdf_directory = r'c:\\Users\\Petazo\\Desktop\\Boletas Jumbo\\descargas\\Banco\\banco de chile\\cuenta corriente'
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
                
                processed_dir = os.path.join(os.path.dirname(pdf_path), 'procesados')
                os.makedirs(processed_dir, exist_ok=True)
                processed_filepath = os.path.join(processed_dir, os.path.basename(pdf_path))
                shutil.move(pdf_path, processed_filepath)
                logging.info(f"Archivo movido a la carpeta de procesados: {processed_filepath}")
                log_file_movement(pdf_path, processed_filepath, "SUCCESS", "Archivo procesado y movido con éxito.")

            except Exception as e:
                logging.error(f"Ocurrió un error procesando el archivo {os.path.basename(pdf_path)}: {e}", exc_info=True)
                log_file_movement(pdf_path, "N/A", "FAILED", f"Error al procesar: {e}")

if __name__ == '__main__':
    main()