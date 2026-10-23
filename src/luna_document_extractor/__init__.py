"""Luna Document Extractor.

Lightweight, offline PDF document extractor & parser for invoices, receipts, and warranties.
"""

from pathlib import Path
from typing import Optional, Union

from luna_document_extractor.extractor import ExtractedDocument, PDFTextExtractor
from luna_document_extractor.parser import DocumentParser
from luna_document_extractor.schemas import (
    DocumentExtractionError,
    DocumentMetadata,
    DocumentType,
    EmptyDocumentError,
    EncryptedPDFError,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
    InvalidPDFError,
    UnsupportedFileFormatError,
)

__version__ = "0.1.0"
__all__ = [
    "__version__",
    "extract_document",
    "PDFTextExtractor",
    "DocumentParser",
    "ExtractedDocument",
    "ExtractionResult",
    "ExtractedField",
    "DocumentMetadata",
    "DocumentType",
    "ExtractionStatus",
    "DocumentExtractionError",
    "InvalidPDFError",
    "EncryptedPDFError",
    "EmptyDocumentError",
    "UnsupportedFileFormatError",
]


def extract_document(
    source: Union[str, Path, bytes],
    document_type: Optional[Union[DocumentType, str]] = None,
    filename: Optional[str] = None,
) -> ExtractionResult:
    """High-level one-step document extraction API.

    Extracts text and parses structured candidate fields from a PDF file
    or byte stream completely offline without external APIs.

    Args:
        source: Path to PDF file (str or Path) or raw PDF bytes.
        document_type: Optional hint to bypass classification
            ('invoice', 'receipt', 'warranty', or DocumentType enum).
        filename: Optional filename hint when source is bytes.

    Returns:
        ExtractionResult containing extracted fields, metadata, status,
        and missing field requirements.

    Example:
        >>> from luna_document_extractor import extract_document
        >>> result = extract_document("tests/fixtures/sample_invoice.pdf")
        >>> print(result.status)
        ExtractionStatus.SUCCESS
        >>> print(result.get_field_value("invoice_number"))
        'INV-2025-001'
    """
    type_hint = None
    if document_type is not None:
        if isinstance(document_type, str):
            type_hint = DocumentType(document_type.lower())
        else:
            type_hint = document_type

    extractor = PDFTextExtractor()
    extracted_doc = extractor.extract(source, filename=filename)

    parser = DocumentParser(document_type_hint=type_hint)
    return parser.parse(extracted_doc)
