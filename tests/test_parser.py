"""Unit tests for document parsing, classification, and field extraction."""

import json
from pathlib import Path

from luna_document_extractor import extract_document
from luna_document_extractor.schemas import (
    DocumentType,
    ExtractionStatus,
)


def test_parse_invoice_document(invoice_pdf_path: Path):
    """Test full parsing lifecycle for a standard tax invoice."""
    result = extract_document(invoice_pdf_path)

    assert result.status == ExtractionStatus.SUCCESS
    assert result.document_type == DocumentType.INVOICE
    assert len(result.missing_fields) == 0

    # Field assertions
    inv_num = result.get_field_value("invoice_number")
    assert inv_num == "INV-2025-9921"
    assert result.fields["invoice_number"].confidence >= 0.90
    assert result.fields["invoice_number"].page_number == 1

    total = result.get_field_value("total_amount")
    assert total == 1650.00
    assert result.fields["total_amount"].confidence >= 0.95

    subtotal = result.get_field_value("subtotal")
    assert subtotal == 1500.00

    tax = result.get_field_value("tax_amount")
    assert tax == 150.00

    inv_date = result.get_field_value("invoice_date")
    assert inv_date == "2025-06-15"

    due_date = result.get_field_value("due_date")
    assert due_date == "2025-07-15"

    currency = result.get_field_value("currency")
    assert currency == "USD"

    customer = result.get_field_value("customer_name")
    assert "Jane Doe" in customer

    vendor = result.get_field_value("vendor_name")
    assert "Acme" in vendor


def test_parse_receipt_document(receipt_pdf_path: Path):
    """Test full parsing lifecycle for a sales receipt."""
    result = extract_document(receipt_pdf_path)

    assert result.status == ExtractionStatus.SUCCESS
    assert result.document_type == DocumentType.RECEIPT

    receipt_num = result.get_field_value("receipt_number")
    assert receipt_num == "RC-88192"

    total = result.get_field_value("total_amount")
    assert total == 89.50

    receipt_date = result.get_field_value("receipt_date")
    assert receipt_date == "2026-10-12"


def test_parse_warranty_document(warranty_pdf_path: Path):
    """Test full parsing lifecycle for a hardware warranty agreement."""
    result = extract_document(warranty_pdf_path)

    assert result.status == ExtractionStatus.SUCCESS
    assert result.document_type == DocumentType.WARRANTY

    term = result.get_field_value("warranty_term")
    assert "2-year" in term.lower()

    serial = result.get_field_value("serial_number")
    assert serial == "SN-ACME-4001"

    product = result.get_field_value("product_name")
    assert "UltraBook Pro 15" in product

    coverage = result.get_field_value("coverage_scope")
    assert "materials" in coverage.lower()

    exclusions = result.get_field_value("exclusions")
    assert "accidental drops" in exclusions.lower()


def test_parse_incomplete_invoice_reports_missing_fields(incomplete_invoice_path: Path):
    """Test that missing required fields are identified and status is PARTIAL."""
    result = extract_document(incomplete_invoice_path)

    assert result.status == ExtractionStatus.PARTIAL
    assert result.document_type == DocumentType.INVOICE
    assert "invoice_number" in result.missing_fields
    assert "total_amount" in result.missing_fields
    # Date was extracted
    assert "invoice_date" in result.fields


def test_parse_empty_document_status(empty_pdf_path: Path):
    """Test that a blank empty PDF returns status EMPTY."""
    result = extract_document(empty_pdf_path)

    assert result.status == ExtractionStatus.EMPTY
    assert result.metadata.has_digital_text is False
    assert len(result.fields) == 0


def test_parse_scanned_document_status(scanned_pdf_path: Path):
    """Test that an image-only scanned PDF returns status NEEDS_OCR with warnings."""
    result = extract_document(scanned_pdf_path)

    assert result.status == ExtractionStatus.NEEDS_OCR
    assert result.metadata.has_digital_text is False
    assert len(result.fields) == 0
    assert any("OCR is not supported" in w for w in result.warnings)


def test_type_hint_override(invoice_pdf_path: Path):
    """Test overriding automatic classification with explicit type hint."""
    # Force classify invoice as generic/unknown
    result = extract_document(invoice_pdf_path, document_type=DocumentType.UNKNOWN)
    assert result.document_type == DocumentType.UNKNOWN


def test_json_serialization(invoice_pdf_path: Path):
    """Test to_dict and to_json output structures."""
    result = extract_document(invoice_pdf_path)

    # 1. to_dict()
    res_dict = result.to_dict()
    assert isinstance(res_dict, dict)
    assert res_dict["status"] == "success"
    assert res_dict["document_type"] == "invoice"
    assert "fields" in res_dict
    assert res_dict["fields"]["invoice_number"]["value"] == "INV-2025-9921"

    # 2. to_json()
    json_str = result.to_json(indent=2)
    parsed = json.loads(json_str)
    assert parsed["metadata"]["filename"] == "sample_invoice.pdf"
    assert parsed["fields"]["total_amount"]["value"] == 1650.00
