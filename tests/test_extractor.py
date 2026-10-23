"""Unit tests for low-level PDF text and layout extraction."""

from pathlib import Path
import pytest

from luna_document_extractor.extractor import PDFTextExtractor
from luna_document_extractor.schemas import (
    EmptyDocumentError,
    EncryptedPDFError,
    InvalidPDFError,
)


def test_extract_valid_invoice_file(invoice_pdf_path: Path):
    """Test extracting text from a physical PDF file path."""
    extractor = PDFTextExtractor()
    doc = extractor.extract(invoice_pdf_path)

    assert doc.filename == "sample_invoice.pdf"
    assert doc.page_count == 1
    assert doc.has_digital_text is True
    assert doc.is_encrypted is False
    assert doc.is_scanned is False
    assert "INV-2025-9921" in doc.full_text
    assert "Acme Electronics Solutions" in doc.full_text
    assert doc.total_characters > 100


def test_extract_from_byte_stream(invoice_pdf_path: Path):
    """Test extracting text from raw PDF bytes."""
    pdf_bytes = invoice_pdf_path.read_bytes()
    extractor = PDFTextExtractor()
    doc = extractor.extract(pdf_bytes, filename="in_memory_invoice.pdf")

    assert doc.filename == "in_memory_invoice.pdf"
    assert doc.page_count == 1
    assert "INV-2025-9921" in doc.full_text


def test_extract_non_existent_file(tmp_path: Path):
    """Test that attempting to open a non-existent file raises InvalidPDFError."""
    extractor = PDFTextExtractor()
    missing_file = tmp_path / "does_not_exist.pdf"

    with pytest.raises(InvalidPDFError, match="File not found"):
        extractor.extract(missing_file)


def test_extract_corrupted_file(tmp_path: Path):
    """Test that a non-PDF corrupted byte stream raises InvalidPDFError."""
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"THIS IS NOT A VALID PDF FILE HEADER")

    extractor = PDFTextExtractor()
    with pytest.raises(InvalidPDFError):
        extractor.extract(corrupt_file)


def test_extract_zero_byte_empty_file(tmp_path: Path):
    """Test that an empty 0-byte file raises EmptyDocumentError."""
    empty_file = tmp_path / "zero_bytes.pdf"
    empty_file.write_bytes(b"")

    extractor = PDFTextExtractor()
    with pytest.raises(EmptyDocumentError, match="empty"):
        extractor.extract(empty_file)


def test_extract_encrypted_password_protected_pdf(encrypted_pdf_path: Path):
    """Test that encrypted PDFs without a password raise EncryptedPDFError."""
    extractor = PDFTextExtractor()

    with pytest.raises(EncryptedPDFError, match="password-protected"):
        extractor.extract(encrypted_pdf_path)


def test_extract_scanned_image_only_pdf(scanned_pdf_path: Path):
    """Test that scanned/image-only PDFs are detected and flagged without OCR error."""
    extractor = PDFTextExtractor()
    doc = extractor.extract(scanned_pdf_path)

    assert doc.has_digital_text is False
    assert doc.is_scanned is True
    assert doc.total_characters == 0
    assert any("OCR is not supported" in w for w in doc.warnings)


def test_extract_blank_empty_pdf(empty_pdf_path: Path):
    """Test extracting a PDF with blank pages (no text, no images)."""
    extractor = PDFTextExtractor()
    doc = extractor.extract(empty_pdf_path)

    assert doc.has_digital_text is False
    assert doc.is_scanned is False
    assert doc.page_count == 1
    assert doc.total_characters == 0
