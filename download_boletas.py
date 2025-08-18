# -*- coding: utf-8 -*-
"""Script para la descarga automatizada de boletas desde Jumbo.cl."""

import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Importar desde el archivo de configuración central
from config import BOLETAS_DIR, MIS_COMPRAS_URL, LOGIN_URL, DOWNLOAD_LOG_FILE

def setup_logging():
    """Configura el sistema de logging para este script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # Guardar logs en un archivo
            logging.FileHandler(DOWNLOAD_LOG_FILE, mode='w'),
            # Mostrar logs en la consola
            logging.StreamHandler()
        ]
    )

def setup_driver():
    """Configura e inicializa el navegador Chrome con Selenium."""
    chrome_options = Options()
    # Deshabilitar notificaciones emergentes de Chrome
    chrome_options.add_argument("--disable-notifications")
    # Configurar preferencias para la descarga de archivos
    prefs = {
        "download.default_directory": BOLETAS_DIR, # Directorio de descarga
        "download.prompt_for_download": False # No preguntar antes de descargar
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Instalar y configurar el driver de Chrome automáticamente
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_downloaded_filenames():
    """Obtiene una lista de los nombres de archivo PDF ya existentes en el directorio."""
    try:
        files = os.listdir(BOLETAS_DIR)
        # Filtrar para devolver solo los archivos PDF
        return [f for f in files if f.endswith('.pdf')]
    except FileNotFoundError:
        return []

def main():
    """Función principal para orquestar la descarga de las boletas."""
    setup_logging()
    driver = setup_driver()
    # Configurar una espera explícita (máximo 20 segundos)
    wait = WebDriverWait(driver, 20)
    
    try:
        logging.info("Abriendo la página de login de Jumbo.cl...")
        driver.get(LOGIN_URL)
        
        # --- Espera de Login Manual ---
        login_wait = WebDriverWait(driver, 180) # Espera hasta 3 minutos
        logging.info("==================================================================")
        logging.info("ACCIÓN REQUERIDA: Por favor, inicia sesión manualmente en la ventana de Chrome.")
        logging.info("El script esperará automáticamente a que inicies sesión...")
        logging.info("==================================================================")
        try:
            login_indicator = (By.XPATH, "//a[@href='/mis-tarjetas']")
            login_wait.until(EC.presence_of_element_located(login_indicator))
            logging.info("¡Login detectado exitosamente!")
        except TimeoutException:
            logging.error("No se detectó el inicio de sesión en el tiempo esperado (3 minutos). Abortando.")
            raise # Lanza la excepción para terminar el script
        
        logging.info("Continuando con el proceso de descarga...")
        driver.get(MIS_COMPRAS_URL)
        
        page_number = 1
        processed_pages_content = set() # Para detectar si una página se repite (bug de la web)

        while True:
            logging.info(f"--- Procesando Página {page_number} ---")
            
            try:
                # Esperar a que al menos un número de pedido esté presente en la página
                wait.until(EC.presence_of_element_located((By.XPATH, "//p[contains(text(),'Número de pedido:')]")))
                time.sleep(4) # Pausa adicional para asegurar que todo el contenido dinámico cargue

                # Obtener todos los elementos de pedido en la página actual
                order_id_elements = driver.find_elements(By.XPATH, "//p[contains(text(),'Número de pedido:')]")
                current_page_content = tuple(elem.text for elem in order_id_elements)

                # Si la página no tiene pedidos o es idéntica a una ya procesada, terminar.
                if not current_page_content or current_page_content in processed_pages_content:
                    logging.warning("Página vacía o repetida detectada. Terminando el proceso.")
                    break
                processed_pages_content.add(current_page_content)

                downloaded_files = get_downloaded_filenames()
                logging.info(f"Se encontraron {len(order_id_elements)} pedidos en la página {page_number}.")

                for i in range(len(order_id_elements)):
                    # Volver a buscar los elementos en cada iteración para evitar errores de "StaleElementReferenceException"
                    current_order_p = driver.find_elements(By.XPATH, "//p[contains(text(),'Número de pedido:')]")[i]
                    order_id = current_order_p.text.split(':')[1].strip()
                    logging.info(f"Procesando pedido: {order_id}")

                    # Verificar si ya existe un PDF que contenga el ID del pedido
                    if any(order_id in fname for fname in downloaded_files):
                        logging.info(f"El pedido {order_id} ya existe. Saltando.")
                        continue
                    
                    try:
                        logging.info(f"Descargando pedido {order_id}...")
                        # Buscar el botón de "Consultar boleta" asociado al pedido actual
                        download_button = current_order_p.find_element(By.XPATH, "./following::button[.//span[contains(text(),'Consultar boleta')]][1]")
                        # Usar JavaScript para hacer clic, es más robusto que el clic directo
                        driver.execute_script("arguments[0].click();", download_button)
                        time.sleep(5) # Esperar a que la descarga se inicie y complete
                        downloaded_files.append(order_id) # Añadir a la lista para no volver a descargarlo en esta misma sesión
                    except Exception as e:
                        logging.error(f"No se pudo procesar la descarga para el pedido {order_id}: {e}")

            except TimeoutException:
                logging.info("No se encontraron más pedidos. Se asume fin de la lista.")
                break

            # --- Paginación ---
            try:
                logging.info("Buscando el botón de 'Siguiente Página'...")
                next_page_button = driver.find_element(By.XPATH, "(//div[@data-testid='icon-container'])[last()]")
                # Mover el botón a la vista para asegurar que no esté obstruido por otros elementos
                driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button)
                time.sleep(1)
                
                driver.execute_script("arguments[0].click();", next_page_button)
                page_number += 1
                logging.info(f"Pasando a la página {page_number}...")
            except NoSuchElementException:
                logging.info("No se encontró el botón de 'Siguiente Página'. Fin de la paginación.")
                break

    except Exception as e:
        logging.error(f"Ocurrió un error fatal en el proceso: {e}")
    finally:
        logging.info("Proceso finalizado. El navegador se cerrará en 20 segundos.")
        time.sleep(20)
        driver.quit()

if __name__ == "__main__":
    main()