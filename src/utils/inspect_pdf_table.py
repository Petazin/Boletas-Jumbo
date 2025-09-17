import pdfplumber
import sys
import pprint

def inspect_pdf(pdf_path):
    """
    Abre un archivo PDF, extrae todas las tablas de todas las páginas
    y las imprime en la consola.
    """
    print(f"--- Inspeccionando tablas en: {pdf_path} ---")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                print("El PDF no tiene páginas.")
                return

            for i, page in enumerate(pdf.pages):
                print(f"\n--- Página {i+1} ---")
                tables = page.extract_tables()
                if not tables:
                    print("No se encontraron tablas en esta página.")
                    continue
                
                for j, table in enumerate(tables):
                    print(f"\n--- Tabla {j+1} en Página {i+1} ---")
                    pprint.pprint(table)

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_file_path = sys.argv[1]
        inspect_pdf(pdf_file_path)
    else:
        print("Por favor, proporciona la ruta al archivo PDF como argumento.")
        print("Uso: python inspect_pdf_table.py RUTA_AL_PDF")
