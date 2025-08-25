# -*- coding: utf-8 -*-
"""Módulo para extraer y procesar datos de boletas en formato PDF."""

import logging
import os
import re
from datetime import datetime  # Importar solo datetime
import pypdf  # Importar pypdf
import shutil  # Importar shutil para mover archivos
import config  # Importar configuración centralizada

from product_categorizer import categorize_product


def parse_chilean_number(num_str):
    """Convierte un string de número con formato chileno a un float."""
    if not num_str:
        return 0.0
    num_str = str(num_str).replace(".", "").replace(" ", "").replace(",", ".")
    return float(num_str)


def quarantine_pdf(pdf_path, error_message):
    """Mueve un PDF a un directorio de cuarentena y registra el error."""
    logging.error(f"PDF en cuarentena: {pdf_path}. Razón: {error_message}")
    quarantine_dir = config.QUARANTINE_DIR
    os.makedirs(quarantine_dir, exist_ok=True)
    try:
        shutil.move(
            pdf_path, os.path.join(quarantine_dir, os.path.basename(pdf_path))
        )
        logging.info(f"PDF movido a cuarentena: {os.path.basename(pdf_path)}")
    except Exception as e:
        logging.error(f"Error al mover PDF a cuarentena {pdf_path}: {e}")


def process_pdf(pdf_path):
    """Extrae toda la información relevante de un único archivo PDF de boleta."""
    logging.info(f"Procesando: {pdf_path}")
    text = ""
    try:
        with open(pdf_path, "rb") as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text.replace("\x00", "") + "\n"

    except Exception as e:
        quarantine_pdf(pdf_path, f"Error al leer PDF: {e}")
        return None, None, None, []

    if not text.strip():
        quarantine_pdf(pdf_path, "PDF vacío o ilegible.")
        return None, None, None, []

    boleta_id_match = re.search(
        config.REGEX_PATTERNS["BOLETA_NUMERO"], text, re.IGNORECASE
    )
    boleta_id = boleta_id_match.group(1) if boleta_id_match else None
    if not boleta_id:
        quarantine_pdf(pdf_path, "No se pudo extraer el ID de boleta.")
        return None, None, None, []

    date_time_match = re.search(
        config.REGEX_PATTERNS["FECHA_HORA"], text, re.DOTALL
    )
    purchase_date = None
    purchase_time = None

    if date_time_match:
        date_str = date_time_match.group(1)
        time_str = date_time_match.group(2)
        try:
            day, month, year_short = date_str.split("/")
            year_full = f"20{year_short}"
            purchase_date = datetime.strptime(
                f"{day}-{month}-{year_full}", "%d-%m-%Y"
            ).date()
            purchase_time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            logging.warning(
                f"Formato de fecha/hora inesperado en {pdf_path}."
            )
            pass

    if not purchase_date:
        date_match_old = re.search(
            config.REGEX_PATTERNS["SALDO_PUNTOS"], text
        )
        if date_match_old:
            try:
                purchase_date = datetime.strptime(
                    date_match_old.group(1), "%d-%m-%Y"
                ).date()
            except ValueError:
                pass

    if not purchase_date:
        filename_match = re.match(
            config.REGEX_PATTERNS["NOMBRE_ARCHIVO_PDF"], os.path.basename(pdf_path)
        )
        if filename_match:
            timestamp_ms = int(filename_match.group(1))
            purchase_date = datetime.fromtimestamp(timestamp_ms / 1000).date()

    if not purchase_date:
        quarantine_pdf(pdf_path, "No se pudo extraer la fecha de compra.")
        return None, None, None, []

    products = {}
    product_pattern = re.compile(
        config.REGEX_PATTERNS["PRODUCTO"], re.MULTILINE
    )
    qty_price_pattern = re.compile(config.REGEX_PATTERNS["CANTIDAD_PRECIO"])
    offer_pattern = re.compile(
        config.REGEX_PATTERNS["OFERTA_DESCUENTO"], re.IGNORECASE
    )

    lines = text.split("\n")
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
                qty_price_match = qty_price_pattern.search(lines[i - 1])
                if qty_price_match:
                    quantity = int(qty_price_match.group(1))
                    unit_price = parse_chilean_number(qty_price_match.group(2))

            if i + 1 < len(lines):
                offer_match = offer_pattern.search(lines[i + 1])
                if offer_match:
                    offer_desc = offer_match.group(1).strip()
                    discount_str = offer_match.group(2)
                    discount = parse_chilean_number(discount_str)

            if sku in products:
                products[sku]["Cantidad_unidades"] += quantity
                products[sku]["Total_a_pagar_producto"] += total
                products[sku]["Cantidad_reducida_del_total"] += discount
            else:
                products[sku] = {
                    "Fecha": purchase_date,
                    "Hora": purchase_time,
                    "codigo_SKU": sku,
                    "Cantidad_unidades": quantity,
                    "Valor_Unitario": unit_price,
                    "Cantidad_comprada_X_Valor_Unitario": (
                        f"{quantity} X ${unit_price:.0f}"
                    ),
                    "Descripcion_producto": description.strip(),
                    "Total_a_pagar_producto": total,
                    "Descripcion_Oferta": offer_desc,
                    "Cantidad_reducida_del_total": discount,
                    "Categoria": categorize_product(description.strip()),
                }

    if not products:
        quarantine_pdf(pdf_path, "No se pudieron extraer productos del PDF.")
        return None, None, None, []

    return boleta_id, purchase_date, purchase_time, list(products.values())
