# -*- coding: utf-8 -*-
"""Módulo para extraer y procesar datos de boletas en formato PDF."""

import logging
import os
import re
from datetime import datetime, time # Importar time también

from product_categorizer import categorize_product

def parse_chilean_number(num_str):
    """Convierte un string de número con formato chileno (ej. '1.234') a un float (1234.0)."""
    # Elimina los separadores de miles (.) y los espacios, y luego convierte a float.
    num_str = str(num_str).replace('.', '').replace(' ', '').replace(',', '')
    return float(num_str)

def process_pdf(pdf_path):
    """Extrae toda la información relevante de un único archivo PDF de boleta.

    Lee el texto del PDF, busca patrones para encontrar el ID de la boleta, la fecha y
    cada uno de los productos con sus detalles (SKU, precio, cantidad, etc.).

    Args:
        pdf_path (str): La ruta completa al archivo PDF que se va a procesar.

    Returns:
        tuple: Una tupla con (boleta_id, purchase_date, purchase_time, products_data).
               Retorna (None, None, None, []) si ocurre un error o no se encuentran datos.
    """
    logging.info(f"Procesando: {pdf_path}")
    text = ""
    try:
        # Abrir el archivo PDF en modo de lectura binaria ('rb')
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            # Iterar por cada página del PDF
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    # Concatenar el texto de cada página, reemplazando caracteres nulos.
                    text += extracted_text.replace('\x00', '') + "\n"
    except Exception as e:
        logging.error(f"Error al leer PDF {pdf_path}: {e}")
        return None, None, None, []

    # --- Extracción de ID de Boleta ---
    # Busca el patrón "BOLETA ELECTRONICA N°..." para obtener el número.
    boleta_id_match = re.search(r"BOLETA\s*ELECTRONICA\s*N\D*(\d+)", text, re.IGNORECASE)
    boleta_id = boleta_id_match.group(1) if boleta_id_match else None
    if not boleta_id:
        logging.warning(f"No se pudo extraer el ID de boleta de {pdf_path}. Saltando.")
        return None, None, None, []

    # --- Extracción de Fecha y Hora (Nuevo método prioritario) ---
    # Busca el patrón "FECHA HORA LOCAL" seguido de la fecha (DD/MM/YY) y la hora (HH:MM)
    # Usamos re.DOTALL para que el '.' incluya saltos de línea si es necesario.
    date_time_match = re.search(r"FECHA\s+HORA LOCAL.*?(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})", text, re.DOTALL)
    purchase_date = None
    purchase_time = None

    if date_time_match:
        date_str = date_time_match.group(1)
        time_str = date_time_match.group(2)
        try:
            # Convertir DD/MM/YY a DD-MM-YYYY. Asumimos que YY es 20YY.
            day, month, year_short = date_str.split('/')
            year_full = f"20{year_short}" # Asumiendo que el año es del siglo 21
            purchase_date = datetime.strptime(f"{day}-{month}-{year_full}", "%d-%m-%Y").date()
            purchase_time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            logging.warning(f"Formato de fecha/hora inesperado en {pdf_path} para el nuevo patrón.")
            pass # Si falla, se intentarn los mtodos antiguos.

    # --- Extracción de Fecha (Métodos antiguos como fallback) ---
    # Si el nuevo método no encontró la fecha, intentar con los métodos anteriores.
    if not purchase_date:
        # Intento 1 (antiguo): Buscar la fecha con el formato "dd-mm-yyyy" cerca del texto de puntos.
        date_match_old = re.search(r"SALDO\s+DE\s+PUNTOS\s+AL\s*(\d{2}[-/]\d{2}[-/]\d{4})", text)
        if date_match_old:
            try:
                purchase_date = datetime.strptime(date_match_old.group(1), "%d-%m-%Y").date()
            except ValueError:
                pass

    if not purchase_date:
        # Intento 2 (antiguo): Si falla lo anterior, intentar deducir la fecha desde el nombre del archivo.
        filename_match = re.match(r"v\d+jmch-\d+_(\d{13})\.pdf", os.path.basename(pdf_path))
        if filename_match:
            # El timestamp en el nombre del archivo es en milisegundos desde la época.
            timestamp_ms = int(filename_match.group(1))
            purchase_date = datetime.fromtimestamp(timestamp_ms / 1000).date()


    if not purchase_date:
        logging.warning(f"No se pudo extraer la fecha de {pdf_path}. Saltando.")
        return boleta_id, None, None, [] # Retornar None para la hora también

    # --- Extracción de Productos ---
    products = {}
    # Expresiones regulares pre-compiladas para eficiencia.
    # 1. Patrón para la línea principal del producto (SKU, Descripción, Total)
    product_pattern = re.compile(r'^\s*(\d{8,13})\s+(.+?)\s+([\d.,]+)\s*$', re.MULTILINE)
    # 2. Patrón para la línea de cantidad y precio unitario (ej. "3 X $1.990")
    qty_price_pattern = re.compile(r'^(\d+)\s*X\s*\$([\d.,]+)')
    # 3. Patrón para la línea de descuento u oferta.
    offer_pattern = re.compile(r'(TMP\s*(?:OFERTA|DESCUENTO).*?)(-?[\d.,]+)\s*$', re.IGNORECASE)

    lines = text.split('\n')
    for i, line in enumerate(lines):
        product_match = product_pattern.search(line)
        if product_match:
            sku, description, total_str = product_match.groups()
            total = parse_chilean_number(total_str)
            
            # Valores por defecto
            quantity = 1
            unit_price = total
            offer_desc = None
            discount = 0.0

            # Buscar cantidad y precio en la línea ANTERIOR
            if i > 0:
                qty_price_match = qty_price_pattern.search(lines[i-1])
                if qty_price_match:
                    quantity = int(qty_price_match.group(1))
                    unit_price = parse_chilean_number(qty_price_match.group(2))

            # Buscar oferta/descuento en la línea SIGUIENTE
            if i + 1 < len(lines):
                offer_match = offer_pattern.search(lines[i+1])
                if offer_match:
                    offer_desc = offer_match.group(1).strip()
                    discount_str = offer_match.group(2)
                    discount = parse_chilean_number(discount_str)

            # Agrupar productos por SKU para consolidar items repetidos
            if sku in products:
                products[sku]['Cantidad_unidades'] += quantity
                products[sku]['Total_a_pagar_producto'] += total
                products[sku]['Cantidad_reducida_del_total'] += discount
            else:
                products[sku] = {
                    'Fecha': purchase_date,
                    'Hora': purchase_time, # Nuevo campo para la hora
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

    return boleta_id, purchase_date, purchase_time, list(products.values())