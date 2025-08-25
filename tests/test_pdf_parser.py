import pytest
import sys
import os
from unittest import mock
from pdf_parser import process_pdf, parse_chilean_number

# Añadir el directorio raíz del proyecto al path para que pueda encontrar pdf_parser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Mock para la función categorize_product
# Esto evita la dependencia real de product_categorizer.py
def test_parse_chilean_number():
    assert parse_chilean_number("1.234.567,89") == 1234567.89
    assert parse_chilean_number("1.000") == 1000.0
    assert parse_chilean_number("500,50") == 500.50
    assert parse_chilean_number("123") == 123.0
    assert parse_chilean_number("0,00") == 0.0
    assert parse_chilean_number("") == 0.0
    assert parse_chilean_number(None) == 0.0
    assert parse_chilean_number(" 1.234 ") == 1234.0


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_success(mock_open, mock_categorize_product):
    # Simular el contenido de un PDF
    import pytest
import sys
import os

# Añadir el directorio raíz del proyecto al path para que pueda encontrar pdf_parser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest import mock
from pdf_parser import process_pdf, parse_chilean_number


# Mock para la función categorize_product
# Esto evita la dependencia real de product_categorizer.py
def test_parse_chilean_number():
    assert parse_chilean_number("1.234.567,89") == 1234567.89
    assert parse_chilean_number("1.000") == 1000.0
    assert parse_chilean_number("500,50") == 500.50
    assert parse_chilean_number("123") == 123.0
    assert parse_chilean_number("0,00") == 0.0
    assert parse_chilean_number("") == 0.0
    assert parse_chilean_number(None) == 0.0
    assert parse_chilean_number(" 1.234 ") == 1234.0


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_success(mock_open, mock_categorize_product):
    # Simular el contenido de un PDF
    pdf_content = """
    BOLETA ELECTRONICA N°12345
    FECHA HORA LOCAL 01/01/23 10:30
    1 X $1.000
    7801234567890 PRODUCTO A 1000
    2 X $1.000
    7809876543210 PRODUCTO B 2000
    TMP OFERTA -500
    SALDO DE PUNTOS AL 01-01-2023
    """
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        # Configure the mock_open to return the pdf_content when read
        mock_open.return_value.read.return_value = pdf_content

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


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_no_boleta_id(mock_open, mock_categorize_product):
    pdf_content = """FECHA HORA LOCAL 01/01/23 10:30
PRODUCTO A 1000"""
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        mock_open.return_value.read.return_value = pdf_content

        boleta_id, _, _, _ = process_pdf("dummy_path.pdf")
        assert boleta_id is None


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_no_date(mock_open, mock_categorize_product):
    pdf_content = """BOLETA ELECTRONICA N°12345
PRODUCTO A 1000"""
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        mock_open.return_value.read.return_value = pdf_content

        _, purchase_date, _, _ = process_pdf("dummy_path.pdf")
        assert purchase_date is None


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_empty_pdf(mock_open, mock_categorize_product):
    pdf_content = ""
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        mock_open.return_value.read.return_value = pdf_content

        boleta_id, purchase_date, purchase_time, products_data = process_pdf(
            "dummy_path.pdf"
        )
        assert boleta_id is None
        assert purchase_date is None
        assert purchase_time is None
        assert products_data == []


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_duplicate_products(mock_open, mock_categorize_product):
    pdf_content = """
    BOLETA ELECTRONICA N°12345
    FECHA HORA LOCAL 01/01/23 10:30
    7801234567890 PRODUCTO A 1000
    1 X $1.000
    7801234567890 PRODUCTO A 1500
    1 X $1.500
    """
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        # Configure the mock_open to return the pdf_content when read
        mock_open.return_value.read.return_value = pdf_content

        _, _, _, products_data = process_pdf("dummy_path.pdf")
        assert len(products_data) == 1  # Should be aggregated

        product = products_data[0]
        assert product["codigo_SKU"] == "7801234567890"
        assert product["Cantidad_unidades"] == 2  # 1 + 1
        assert product["Total_a_pagar_producto"] == 2500.0  # 1000 + 1500
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        # Configure the mock_open to return the pdf_content when read
        mock_open.return_value.read.return_value = pdf_content

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


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_no_boleta_id(mock_open, mock_categorize_product):
    pdf_content = """FECHA HORA LOCAL 01/01/23 10:30
PRODUCTO A 1000"""
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        mock_open.return_value.read.return_value = pdf_content

        boleta_id, _, _, _ = process_pdf("dummy_path.pdf")
        assert boleta_id is None


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_no_date(mock_open, mock_categorize_product):
    pdf_content = """BOLETA ELECTRONICA N°12345
PRODUCTO A 1000"""
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        mock_open.return_value.read.return_value = pdf_content

        _, purchase_date, _, _ = process_pdf("dummy_path.pdf")
        assert purchase_date is None


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_empty_pdf(mock_open, mock_categorize_product):
    pdf_content = ""
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        mock_open.return_value.read.return_value = pdf_content

        boleta_id, purchase_date, purchase_time, products_data = process_pdf(
            "dummy_path.pdf"
        )
        assert boleta_id is None
        assert purchase_date is None
        assert purchase_time is None
        assert products_data == []


@mock.patch("pdf_parser.categorize_product", return_value="Categoria Mock")
@mock.patch("builtins.open", new_callable=mock.mock_open)
def test_process_pdf_duplicate_products(mock_open, mock_categorize_product):
    pdf_content = """
    BOLETA ELECTRONICA N°12345
    FECHA HORA LOCAL 01/01/23 10:30
    7801234567890 PRODUCTO A 1000
    1 X $1.000
    7801234567890 PRODUCTO A 1500
    1 X $1.500
    """
    with mock.patch("pdf_parser.pypdf.PdfReader") as MockPdfReaderClass:
        mock_reader_instance = mock.Mock()
        mock_page = mock.Mock()
        mock_page.extract_text.return_value = pdf_content
        mock_reader_instance.pages = [mock_page]
        MockPdfReaderClass.return_value = mock_reader_instance

        # Configure the mock_open to return the pdf_content when read
        mock_open.return_value.read.return_value = pdf_content

        _, _, _, products_data = process_pdf("dummy_path.pdf")
        assert len(products_data) == 1  # Should be aggregated

        product = products_data[0]
        assert product["codigo_SKU"] == "7801234567890"
        assert product["Cantidad_unidades"] == 2  # 1 + 1
        assert product["Total_a_pagar_producto"] == 2500.0  # 1000 + 1500