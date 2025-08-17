import logging
import os
import re
from datetime import datetime
import PyPDF2
from database_utils import db_connection

# Importar desde el archivo de configuración central
from config import DB_CONFIG, BOLETAS_DIR, PROCESS_LOG_FILE

from product_categorizer import categorize_product

# --- Función para parsear números chilenos ---
def parse_chilean_number(num_str):
    num_str = str(num_str).replace('.', '').replace(' ', '').replace(',', '')
    return float(num_str)

# --- Función para procesar un archivo PDF ---
def process_pdf(pdf_path):
    logging.info(f"Procesando: {pdf_path}")
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text.replace('\x00', '') + "\n"
    except Exception as e:
        logging.error(f"Error al leer PDF {pdf_path}: {e}")
        return None, None, []

    boleta_id_match = re.search(r"BOLETA\s*ELECTRONICA\s*N\D*(\d+)", text, re.IGNORECASE)
    boleta_id = boleta_id_match.group(1) if boleta_id_match else None
    if not boleta_id:
        logging.warning(f"No se pudo extraer el ID de boleta de {pdf_path}. Saltando.")
        return None, None, []

    date_match = re.search(r"SALDO\s+DE\s+PUNTOS\s+AL\s*(\d{{2}}[-/]\d{{2}}[-/]\d{{4}})", text)
    purchase_date = None
    if date_match:
        try:
            purchase_date = datetime.strptime(date_match.group(1), "%d-%m-%Y").date()
        except ValueError:
            pass
    if not purchase_date:
        filename_match = re.match(r"(\d{{4}})(\d{{2}})\.pdf", os.path.basename(pdf_path))
        if filename_match:
            try:
                purchase_date = datetime(int(filename_match.group(1)), int(filename_match.group(2)), 1).date()
            except ValueError:
                pass
    if not purchase_date:
        logging.warning(f"No se pudo extraer la fecha de {pdf_path}. Saltando.")
        return boleta_id, None, []

    products = {}
    product_pattern = re.compile(r'^\s*(\d{{8,13}})\s+(.+?)\s+([\d.,]+)\s*, re.MULTILINE)
    qty_price_pattern = re.compile(r'^(\d+)\s*X\s*\$([\d.,]+)')
    offer_pattern = re.compile(r'(TMP\s*(?:OFERTA|DESCUENTO).*?)(-?[\d.,]+)\s*, re.IGNORECASE)

    lines = text.split('\n')
    for i, line in enumerate(lines):
        product_match = product_pattern.search(line)
        if product_match:
            sku, description, total_str = product_match.groups()
            total = parse_chilean_number(total_str)
            
            quantity = 1
            unit_price = total
            offer_desc = None
            discount = 0.0

            if i > 0:
                qty_price_match = qty_price_pattern.search(lines[i-1])
                if qty_price_match:
                    quantity = int(qty_price_match.group(1))
                    unit_price = parse_chilean_number(qty_price_match.group(2))

            if i + 1 < len(lines):
                offer_match = offer_pattern.search(lines[i+1])
                if offer_match:
                    offer_desc = offer_match.group(1).strip()
                    discount_str = offer_match.group(2)
                    discount = parse_chilean_number(discount_str)

            if sku in products:
                products[sku]['Cantidad_unidades'] += quantity
                products[sku]['Total_a_pagar_producto'] += total
                products[sku]['Cantidad_reducida_del_total'] += discount
            else:
                products[sku] = {
                    'Fecha': purchase_date,
                    'codigo_SKU': sku,
                    'Cantidad_unidades': quantity,
                    'Valor_Unitario': unit_price,
                    'Cantidad_comprada_X_Valor_Unitario': f"{quantity} X ${unit_price:.0f}",
                    'Descripcion_producto': description.strip(),
                    'Total_a_pagar_producto': total,
                    'Descripcion_Oferta': offer_desc,
                    'Cantidad_reducida_del_total': discount,
                    'Categoria': categorize_product(description.strip())
                }

    return boleta_id, purchase_date, list(products.values())

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(PROCESS_LOG_FILE, mode='w'),
            logging.StreamHandler()
        ]
    )
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        create_table_query = """
        CREATE TABLE IF NOT EXISTS boletas_data (
            boleta_id VARCHAR(255),
            filename VARCHAR(255), 
            Fecha DATE,
            codigo_SKU VARCHAR(255),
            Cantidad_unidades INT, 
            Valor_Unitario DECIMAL(15, 2),
            Cantidad_comprada_X_Valor_Unitario VARCHAR(255),
            Descripcion_producto TEXT,
            Total_a_pagar_producto DECIMAL(15, 2),
            Descripcion_Oferta TEXT,
            Cantidad_reducida_del_total DECIMAL(15, 2),
            Categoria VARCHAR(255),
            PRIMARY KEY (boleta_id, codigo_SKU)
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        logging.info("Tabla 'boletas_data' verificada/creada exitosamente.")

        pdf_files = [f for f in os.listdir(BOLETAS_DIR) if f.endswith('.pdf')]
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(BOLETAS_DIR, pdf_file)
            
            if pdf_file.lower() == 'contexto.txt': continue

            boleta_id, purchase_date, products_data = process_pdf(pdf_path)

            if boleta_id and purchase_date and products_data:
                check_query = "SELECT 1 FROM boletas_data WHERE filename = %s LIMIT 1"
                cursor.execute(check_query, (os.path.basename(pdf_path),))
                if cursor.fetchone():
                    logging.info(f"El archivo {pdf_file} ya fue procesado. Saltando.")
                    continue

                insert_query = """
                INSERT INTO boletas_data (
                    boleta_id, filename, Fecha, codigo_SKU, Cantidad_unidades, Valor_Unitario, Cantidad_comprada_X_Valor_Unitario,
                    Descripcion_producto, Total_a_pagar_producto,
                    Descripcion_Oferta, Cantidad_reducida_del_total, Categoria
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    Cantidad_unidades=VALUES(Cantidad_unidades), Valor_Unitario=VALUES(Valor_Unitario),
                    Cantidad_comprada_X_Valor_Unitario=VALUES(Cantidad_comprada_X_Valor_Unitario),
                    Descripcion_producto=VALUES(Descripcion_producto), Total_a_pagar_producto=VALUES(Total_a_pagar_producto),
                    Descripcion_Oferta=VALUES(Descripcion_Oferta), Cantidad_reducida_del_total=VALUES(Cantidad_reducida_del_total),
                    Categoria=VALUES(Categoria);
                """
                for product in products_data:
                    try:
                        cursor.execute(insert_query, (
                            boleta_id,
                            os.path.basename(pdf_path),
                            product['Fecha'],
                            product['codigo_SKU'],
                            product['Cantidad_unidades'],
                            product['Valor_Unitario'],
                            product['Cantidad_comprada_X_Valor_Unitario'],
                            product['Descripcion_producto'],
                            product['Total_a_pagar_producto'],
                            product['Descripcion_Oferta'],
                            product['Cantidad_reducida_del_total'],
                            product['Categoria']
                        ))
                    except mysql.connector.Error as err:
                        logging.error(f"Error al insertar datos para SKU {product.get('codigo_SKU', 'N/A')} de {pdf_file}: {err}")
                conn.commit()
            else:
                logging.warning(f"No se pudo procesar completamente {pdf_file}. Saltando.")

        logging.info("\nProceso completado. Revisa tu base de datos MySQL.")

    except mysql.connector.Error as err:
        logging.error(f"Error de conexión a la base de datos: {err}")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
