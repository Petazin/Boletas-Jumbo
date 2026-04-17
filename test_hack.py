from test_ingesta import test_upload
import os

pdf_path = os.path.join("archivos_prueba", "cartola cuenta corriente enero banco de chile.pdf")
test_upload(pdf_path, "Banco_Chile", "Cartola_CC")
