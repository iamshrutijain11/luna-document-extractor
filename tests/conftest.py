"""Pytest fixtures and programmatic synthetic PDF generators for testing."""

import io
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import pytest


def create_synthetic_invoice_pdf() -> bytes:
    """Generate a clean text-based invoice PDF in memory."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # US Letter

    text = """
    Acme Electronics Solutions Inc.
    100 Technology Parkway, Suite 400
    San Francisco, CA 94105
    contact@acmesolutions.example.com

    TAX INVOICE
    Invoice Number: INV-2025-9921
    Invoice Date: 2025-06-15
    Due Date: 2025-07-15

    Bill To: Jane Doe
    Customer ID: CUST-8819
    742 Evergreen Terrace
    Springfield, OR 97477

    ----------------------------------------------------------------------
    Description                        Qty     Unit Price      Amount
    ----------------------------------------------------------------------
    Enterprise Cloud Station            1       $1,200.00   $1,200.00
    Extended Care Service               1         $300.00     $300.00
    ----------------------------------------------------------------------
    Subtotal: $1,500.00
    Sales Tax (10.0%): $150.00
    Total Amount Due: $1,650.00 USD
    ----------------------------------------------------------------------

    Payment Terms: Net 30 days. Thank you for your business!
    """
    page.insert_text((50, 70), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_receipt_pdf() -> bytes:
    """Generate a clean text-based sales receipt PDF in memory."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    text = """
    Metro Market Retail Ltd
    Store #402 - Downtown Seattle
    Register #04  Cashier: Alex

    SALES RECEIPT
    Receipt #: RC-88192
    Date: October 12, 2026

    Items Purchased:
    - Organic Apples: $4.50
    - Whole Grain Bread: $3.80
    - Wireless Optical Mouse: $39.99
    - USB-C Hub: $41.21

    Subtotal: $89.50
    Total Paid: $89.50
    Payment Method: Visa ending in 4242

    Change Due: $0.00
    Thank you for shopping at Metro Market!
    """
    page.insert_text((50, 70), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_warranty_pdf() -> bytes:
    """Generate a clean text-based hardware warranty terms PDF."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    text = """
    Apex Hardware Technologies
    Official Product Warranty Statement

    Product Name: UltraBook Pro 15 Laptop
    Serial Number: SN-ACME-4001
    Date of Purchase: June 15, 2025

    Warranty Term: 2-year limited hardware warranty from date of invoice.

    Coverage Scope:
    Covers defects in materials and hardware components under normal consumer use.

    Exclusions:
    Does not cover accidental drops, liquid spills, normal wear and tear, or software issues.

    Required for Claim:
    Valid proof of purchase, machine serial number, and description of hardware failure.
    """
    page.insert_text((50, 70), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_empty_pdf() -> bytes:
    """Generate a 1-page completely blank PDF with no text or images."""
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_scanned_pdf() -> bytes:
    """Generate an image-only PDF containing no digital text layer."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Create dummy 100x100 RGB image
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    # Insert image on page
    rect = fitz.Rect(100, 100, 400, 400)
    page.insert_image(rect, stream=img_bytes)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_encrypted_pdf(password: str = "SecretPass123") -> bytes:
    """Generate a password-protected encrypted PDF."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 70), "CONFIDENTIAL FINANCIAL DOCUMENT", fontsize=12)

    # Save with user password encryption (AES-256 / permissions)
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
    )
    pdf_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="OwnerPass999",
        user_pw=password,
        permissions=perm,
    )
    doc.close()
    return pdf_bytes


def create_synthetic_incomplete_invoice_pdf() -> bytes:
    """Generate an invoice missing both invoice number and total amount."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    text = """
    Acme Electronics Solutions Inc.
    Date: 2025-06-15

    Bill To: Jane Doe
    This is an unfinalized estimate memo.
    No invoice number has been assigned yet.
    """
    page.insert_text((50, 70), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures writing files to temporary directories
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def invoice_pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample_invoice.pdf"
    path.write_bytes(create_synthetic_invoice_pdf())
    return path


@pytest.fixture
def receipt_pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample_receipt.pdf"
    path.write_bytes(create_synthetic_receipt_pdf())
    return path


@pytest.fixture
def warranty_pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample_warranty.pdf"
    path.write_bytes(create_synthetic_warranty_pdf())
    return path


@pytest.fixture
def empty_pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "empty_doc.pdf"
    path.write_bytes(create_synthetic_empty_pdf())
    return path


@pytest.fixture
def scanned_pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "scanned_doc.pdf"
    path.write_bytes(create_synthetic_scanned_pdf())
    return path


@pytest.fixture
def encrypted_pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "encrypted_doc.pdf"
    path.write_bytes(create_synthetic_encrypted_pdf("SecretPass123"))
    return path


@pytest.fixture
def incomplete_invoice_path(tmp_path: Path) -> Path:
    path = tmp_path / "incomplete_invoice.pdf"
    path.write_bytes(create_synthetic_incomplete_invoice_pdf())
    return path
