# -*- coding: utf-8 -*-
"""Script para la descarga automatizada de boletas desde Jumbo.cl."""

import time
import logging
import os
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import hashlib

# Importar desde el archivo de configuración central
from config import (
    DOWNLOADS_DIR,
    ORGANIZED_DIR,
    MIS_COMPRAS_URL,
    LOGIN_URL,
    DOWNLOAD_LOG_FILE,
    CURRENT_SOURCE,
)
from database_utils import (
    get_downloaded_order_ids,
    insert_download_history,
)
from pdf_parser import process_pdf

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


def setup_logging():
    """Configura el sistema de logging para este script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(DOWNLOAD_LOG_FILE, mode="w"),
            logging.StreamHandler(),
        ],
    )


def setup_driver():
    """Configura e inicializa el navegador Chrome con Selenium."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    prefs = {
        "download.default_directory": DOWNLOADS_DIR,
        "download.prompt_for_download": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def process_downloaded_file(order_id):
    """Procesa el archivo PDF recién descargado."""
    try:
        time.sleep(5)
        files = os.listdir(DOWNLOADS_DIR)
        pdf_files = [f for f in files if f.endswith(".pdf")]
        if not pdf_files:
            logging.error(
                f"No se encontró ningún archivo PDF para el pedido {order_id}"
            )
            return

        latest_file = max(
            pdf_files, key=lambda f: os.path.getmtime(os.path.join(DOWNLOADS_DIR, f))
        )
        original_filepath = os.path.join(DOWNLOADS_DIR, latest_file)

        file_hash = calculate_file_hash(original_filepath)

        boleta_id, purchase_date, purchase_time, products_data, _ = process_pdf(
            original_filepath
        )
        if not boleta_id:
            logging.error(
                f"No se pudieron extraer datos del PDF para el pedido {order_id}"
            )
            return

        total_amount = sum(p["precio_total_item"] for p in products_data)
        item_count = len(products_data)

        date_str = purchase_date.strftime("%Y-%m-%d")
        new_filename = f"{order_id}_{date_str}.pdf"

        os.makedirs(ORGANIZED_DIR, exist_ok=True)
        new_filepath = os.path.join(ORGANIZED_DIR, new_filename)

        shutil.move(original_filepath, new_filepath)
        logging.info(f"Archivo movido y renombrado a: {new_filepath}")

        insert_download_history(
            order_id=order_id,
            fuente=CURRENT_SOURCE,
            fecha_compra=purchase_date,
            fecha_descarga=datetime.now(),
            nombre_archivo_original=latest_file,
            nuevo_nombre_archivo=new_filename,
            ruta_archivo=new_filepath,
            monto_total=total_amount,
            cantidad_items=item_count,
            estado="Descargado",
            file_hash=file_hash
        )

    except Exception as e:
        logging.error(
            f"Error procesando el archivo descargado para el pedido {order_id}: {e}"
        )


def main():
    """Función principal para orquestar la descarga de las boletas."""
    setup_logging()

    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    try:
        logging.info("Abriendo la página de login de Jumbo.cl...")
        driver.get(LOGIN_URL)

        login_wait = WebDriverWait(driver, 180)
        logging.info(
            "=================================================================="
        )
        logging.info(
            "ACCIÓN REQUERIDA: Por favor, inicia sesión manualmente "
            "en la ventana de Chrome."
        )
        logging.info("El script esperará automáticamente a que inicies sesión...")
        logging.info(
            "=================================================================="
        )
        try:
            login_indicator = (By.XPATH, "//a[@href='/mis-tarjetas']")
            login_wait.until(EC.presence_of_element_located(login_indicator))
            logging.info("¡Login detectado exitosamente!")
        except TimeoutException:
            logging.error(
                "No se detectó el inicio de sesión en el tiempo esperado "
                "(3 minutos). Abortando."
            )
            raise

        logging.info("Continuando con el proceso de descarga...")
        driver.get(MIS_COMPRAS_URL)

        page_number = 1
        processed_pages_content = set()

        while True:
            logging.info(f"--- Procesando Página {page_number} ---")

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//p[contains(text(),'Número de pedido:')]")
                    )
                )
                time.sleep(4)

                # Obtenemos el texto del primer pedido en la página para saber cuándo ha cambiado.
                first_order_text_on_page = driver.find_element(By.XPATH, "(//p[contains(text(),'Número de pedido:')])[1]").text

                order_id_elements = driver.find_elements(
                    By.XPATH, "//p[contains(text(),'Número de pedido:')]"
                )
                current_page_content = tuple(elem.text for elem in order_id_elements)

                if (
                    not current_page_content
                    or current_page_content in processed_pages_content
                ):
                    logging.warning(
                        "Página vacía o repetida detectada. Terminando el proceso."
                    )
                    break
                processed_pages_content.add(current_page_content)

                downloaded_order_ids = get_downloaded_order_ids()
                msg = (
                    f"Se encontraron {len(order_id_elements)} pedidos en la página "
                    f"{page_number}."
                )
                logging.info(msg)

                for i in range(len(order_id_elements)):
                    current_order_p = driver.find_elements(
                        By.XPATH, "//p[contains(text(),'Número de pedido:')]"
                    )[i]
                    order_id = current_order_p.text.split(":")[1].strip()
                    logging.info(f"Procesando pedido: {order_id}")

                    if order_id in downloaded_order_ids:
                        msg = (
                            f"El pedido {order_id} ya existe en la base de datos. "
                            "Saltando."
                        )
                        logging.info(msg)
                        continue

                    try:
                        logging.info(f"Descargando pedido {order_id}...")
                        xpath = (
                            "./following::button"
                            "[.//span[contains(text(),'Consultar boleta')]][1]"
                        )
                        download_button = current_order_p.find_element(
                            By.XPATH, xpath
                        )
                        driver.execute_script(
                            "arguments[0].click();", download_button
                        )

                        process_downloaded_file(order_id)

                    except Exception as e:
                        logging.error(
                            f"No se pudo procesar la descarga para el pedido "
                            f"{order_id}: {e}"
                        )

            except TimeoutException:
                logging.info(
                    "No se encontraron más pedidos. Se asume fin de la lista."
                )
                break

            try:
                # --- NEW PAGINATION LOGIC ---
                logging.info("Iniciando nueva lógica de paginación por número.")

                # 1. Encontrar el número de la página activa actual
                active_page_element = driver.find_element(By.XPATH, "//div[contains(@class, 'cux-bg-primary')]/p")
                current_page_number = int(active_page_element.text)
                logging.info(f"Página activa actual detectada: {current_page_number}")

                # 2. Calcular y buscar el botón de la siguiente página
                next_page_number = current_page_number + 1
                logging.info(f"Buscando el botón para la página {next_page_number}...")
                
                next_page_button_xpath = f"//div[@role='button'][.//p[text()='{next_page_number}']]"
                next_page_button = driver.find_element(By.XPATH, next_page_button_xpath)

                # Guardar referencia de la página actual para la espera inteligente
                first_order_text_on_page = driver.find_element(By.XPATH, "(//p[contains(text(),'Número de pedido:')])[1]").text

                # 3. Hacer clic en el botón de la siguiente página
                driver.execute_script("arguments[0].click();", next_page_button)

                # 4. Esperar a que el contenido de la página cambie
                logging.info("Esperando que la página actual se actualice...")
                wait.until(
                    lambda d: d.find_element(By.XPATH, "(//p[contains(text(),'Número de pedido:')])[1]").text != first_order_text_on_page
                )
                logging.info("La página se ha actualizado.")

                page_number = next_page_number # Actualizar nuestro contador de página

            except NoSuchElementException:
                logging.info(
                    "No se encontró el botón para la siguiente página. Fin de la paginación."
                )
                break
    except Exception as e:
        logging.error(f"Ocurrió un error fatal en el proceso: {e}")
    finally:
        logging.info("Proceso finalizado. El navegador se cerrará en 20 segundos.")
        time.sleep(20)
        driver.quit()


if __name__ == "__main__":
    main()
