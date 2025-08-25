import pytest
import sys
import os
from unittest import mock

# Añadir el directorio raíz del proyecto al path para que pueda encontrar pdf_parser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_parser import parse_chilean_number, process_pdf


# Mock para la función categorize_product
# Esto evita la dependencia real de product_categorizer.py
@pytest.mark.skip(reason="Pendiente: Mockeo avanzado de pypdf.PdfReader")
@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
def test_process_pdf_success(mock_categorize_product):
    # Simular el contenido de un PDF
    pdf_content = """
    BOLETA ELECTRONICA N°12345
    FECHA HORA LOCAL 01/01/23 10:30
    7801234567890 PRODUCTO A 1000
    1 X $1.000
    7809876543210 PRODUCTO B 2000
    2 X $1.000
    TMP OFERTA -500
    SALDO DE PUNTOS AL 01-01-2023
    """
    with mock.patch(
        "builtins.open", mock.mock_open(read_data=pdf_content)
    ) as mock_file_open:
        with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
            mock_reader_instance = mock.Mock()
            mock_page = mock.Mock()
            mock_page.extract_text.return_value = pdf_content
            mock_reader_instance.pages = [mock_page]
            MockPdfReaderClass.return_value = mock_reader_instance

        boleta_id, purchase_date, purchase_time, products_data = process_pdf(
            "dummy_path.pdf"
        )

        assert boleta_id == "12345"
        assert (
            purchase_date.year == 2023
            and purchase_date.month == 1
            and purchase_date.day == 1
        )
        assert purchase_time.hour == 10 and purchase_time.minute == 30
        assert len(products_data) == 2

        # Verificar Producto A
        product_a = next(p for p in products_data if p["codigo_SKU"] == "7801234567890")
        assert product_a["Descripcion_producto"] == "PRODUCTO A"
        assert product_a["Cantidad_unidades"] == 1
        assert product_a["Valor_Unitario"] == 1000.0
        assert product_a["Total_a_pagar_producto"] == 1000.0
        assert product_a["Descripcion_Oferta"] is None
        assert product_a["Cantidad_reducida_del_total"] == 0.0
        assert product_a["Categoria"] == "Categoria Mock"

        # Verificar Producto B con oferta
        product_b = next(p for p in products_data if p["codigo_SKU"] == "7809876543210")
        assert product_b["Descripcion_producto"] == "PRODUCTO B"
        assert product_b["Cantidad_unidades"] == 2
        assert product_b["Valor_Unitario"] == 1000.0
        assert product_b["Total_a_pagar_producto"] == 2000.0
        assert product_b["Descripcion_Oferta"] == "TMP OFERTA"
        assert product_b["Cantidad_reducida_del_total"] == -500.0
        assert product_b["Categoria"] == "Categoria Mock"

        mock_categorize_product.assert_called()  # Asegurarse de que se llamó a la función mock


@pytest.mark.skip(reason="Pendiente: Mockeo avanzado de pypdf.PdfReader")
@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
def test_process_pdf_no_boleta_id(mock_categorize_product):
    pdf_content = "FECHA HORA LOCAL 01/01/23 10:30\nPRODUCTO A 1000"
    with mock.patch(
        "builtins.open", mock.mock_open(read_data=pdf_content)
    ) as mock_file_open:
        with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
            mock_reader_instance = mock.Mock()
            mock_page = mock.Mock()
            mock_page.extract_text.return_value = pdf_content
            mock_reader_instance.pages = [mock_page]
            MockPdfReaderClass.return_value = mock_reader_instance

        boleta_id, _, _, _ = process_pdf("dummy_path.pdf")
        assert boleta_id is None


@pytest.mark.skip(reason="Pendiente: Mockeo avanzado de pypdf.PdfReader")
@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
def test_process_pdf_no_date(mock_categorize_product):
    pdf_content = "BOLETA ELECTRONICA N°12345\nPRODUCTO A 1000"
    with mock.patch(
        "builtins.open", mock.mock_open(read_data=pdf_content)
    ) as mock_file_open:
        with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
            mock_reader_instance = mock.Mock()
            mock_page = mock.Mock()
            mock_page.extract_text.return_value = pdf_content
            mock_reader_instance.pages = [mock_page]
            MockPdfReaderClass.return_value = mock_reader_instance

        _, purchase_date, _, _ = process_pdf("dummy_path.pdf")
        assert purchase_date is None


@pytest.mark.skip(reason="Pendiente: Mockeo avanzado de pypdf.PdfReader")
@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
def test_process_pdf_empty_pdf(mock_categorize_product):
    pdf_content = ""
    with mock.patch(
        "builtins.open", mock.mock_open(read_data=pdf_content)
    ) as mock_file_open:
        with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
            mock_reader_instance = mock.Mock()
            mock_page = mock.Mock()
            mock_page.extract_text.return_value = pdf_content
            mock_reader_instance.pages = [mock_page]
            MockPdfReaderClass.return_value = mock_reader_instance

        boleta_id, purchase_date, purchase_time, products_data = process_pdf(
            "dummy_path.pdf"
        )
        assert boleta_id is None
        assert purchase_date is None
        assert purchase_time is None
        assert products_data == []


@pytest.mark.skip(reason="Pendiente: Mockeo avanzado de pypdf.PdfReader")
@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
def test_process_pdf_duplicate_products(mock_categorize_product):
    pdf_content = """
    BOLETA ELECTRONICA N°12345
    FECHA HORA LOCAL 01/01/23 10:30
    7801234567890 PRODUCTO A 1000
    1 X $1.000
    7801234567890 PRODUCTO A 1500
    1 X $1.500
    """
    with mock.patch(
        "builtins.open", mock.mock_open(read_data=pdf_content)
    ) as mock_file_open:
        with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
            mock_reader_instance = mock.Mock()
            mock_page = mock.Mock()
            mock_page.extract_text.return_value = pdf_content
            mock_reader_instance.pages = [mock_page]
            MockPdfReaderClass.return_value = mock_reader_instance

        _, _, _, products_data = process_pdf("dummy_path.pdf")
        assert len(products_data) == 1  # Should be aggregated

        product = products_data[0]
        assert product["codigo_SKU"] == "7801234567890"
        assert product["Cantidad_unidades"] == 2  # 1 + 1
        assert product["Total_a_pagar_producto"] == 2500.0  # 1000 + 1500
