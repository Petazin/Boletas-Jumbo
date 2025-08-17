import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN ---
DOWNLOAD_DIR = r"c:\Users\Petazo\Desktop\Boletas Jumbo"
MIS_COMPRAS_URL = "https://www.jumbo.cl/mis-compras"
LOG_FILE = os.path.join(DOWNLOAD_DIR, "download_boletas.log")

# --- FIN DE LA CONFIGURACIÓN ---

def setup_logging():
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, mode='w'),
            logging.StreamHandler()
        ]
    )

def setup_driver():
    """Configura el navegador Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    prefs = {"download.default_directory": DOWNLOAD_DIR, "download.prompt_for_download": False}
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_downloaded_filenames():
    """Obtiene una lista de los nombres de archivo PDF en el directorio de descargas."""
    try:
        files = os.listdir(DOWNLOAD_DIR)
        return [f for f in files if f.endswith('.pdf')]
    except FileNotFoundError:
        return []

def main():
    """Función principal para descargar las boletas."""
    setup_logging()
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        logging.info("Abriendo la página de login de Jumbo.cl...")
        driver.get("https://www.jumbo.cl/login")
        
        logging.info("==================================================================")
        logging.info("ACCIÓN REQUERIDA: Por favor, inicia sesión manualmente.")
        logging.info("Una vez dentro, vuelve a esta ventana y presiona 'Enter'.")
        logging.info("==================================================================")
        input("Presiona Enter aquí para continuar... ")
        
        logging.info("Continuando con el proceso de descarga...")
        driver.get(MIS_COMPRAS_URL)
        
        page_number = 1
        processed_pages_content = set()

        while True:
            logging.info(f"--- Procesando Página {page_number} ---")
            
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//p[contains(text(),'Número de pedido:')]")))
                time.sleep(4)

                order_id_elements = driver.find_elements(By.XPATH, "//p[contains(text(),'Número de pedido:')]")
                current_page_content = tuple(elem.text for elem in order_id_elements)

                if not current_page_content or current_page_content in processed_pages_content:
                    logging.warning("Página vacía o repetida detectada. Terminando el proceso.")
                    break
                processed_pages_content.add(current_page_content)

                downloaded_files = get_downloaded_filenames()
                logging.info(f"Se encontraron {len(order_id_elements)} pedidos en la página {page_number}.")

                for i in range(len(order_id_elements)):
                    current_order_p = driver.find_elements(By.XPATH, "//p[contains(text(),'Número de pedido:')]")[i]
                    order_id = current_order_p.text.split(':')[1].strip()
                    logging.info(f"Procesando pedido: {order_id}")

                    if any(order_id in fname for fname in downloaded_files):
                        logging.info(f"El pedido {order_id} ya existe. Saltando.")
                        continue
                    
                    try:
                        logging.info(f"Descargando pedido {order_id}...")
                        download_button = current_order_p.find_element(By.XPATH, "./following::button[.//span[contains(text(),'Consultar boleta')]][1]")
                        driver.execute_script("arguments[0].click();", download_button)
                        time.sleep(5)
                        downloaded_files.append(order_id)
                    except Exception as e:
                        logging.error(f"No se pudo procesar la descarga para el pedido {order_id}: {e}")

            except TimeoutException:
                logging.info("No se encontraron más pedidos. Se asume fin de la lista.")
                break

            # --- Paginación ---
            try:
                logging.info("Buscando el botón de 'Siguiente Página'...")
                next_page_button = driver.find_element(By.XPATH, "(//div[@data-testid='icon-container'])[last()]")
                # Mover el botón a la vista para asegurar que no esté obstruido
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