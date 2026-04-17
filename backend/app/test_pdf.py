import pdfplumber
import io

def test_extract(filepath):
    try:
        with open(filepath, "rb") as f:
            pdf_bytes = f.read()
            
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        print("TEXT EXTRACTED:")
        print(text[:2000])
        print("LEN:", len(text))
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    test_extract("/app/app/archivos_fuente/debug.pdf") # Will use mounted path for testing
