"""Data schemas, enums, models, and exceptions for Luna Document Extractor."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    """Supported document classifications."""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    WARRANTY = "warranty"
    UNKNOWN = "unknown"


class ExtractionStatus(str, Enum):
    """Overall status of the document extraction process."""
    SUCCESS = "success"          # Document extracted with all essential fields
    PARTIAL = "partial"          # Extracted some fields, but essential info missing
    NEEDS_OCR = "needs_ocr"      # Scanned image-only PDF; OCR not supported offline
    EMPTY = "empty"              # Zero pages or completely blank document
    FAILED = "failed"            # Error encountered (e.g. corrupt or encrypted)


# ─────────────────────────────────────────────────────────────────────────────
# Field & Result Models
# ─────────────────────────────────────────────────────────────────────────────

class ExtractedField(BaseModel):
    """Represents a single extracted data element with provenance and confidence."""
    model_config = ConfigDict(frozen=True)

    key: str = Field(..., description="Canonical field identifier (e.g., 'invoice_number')")
    value: Union[str, float, int, List[Any], Dict[str, Any]] = Field(
        ..., description="Normalized parsed value"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Extraction confidence score from 0.0 to 1.0"
    )
    raw_text: str = Field(
        ..., description="Exact raw text snippet from the document where the value was found"
    )
    page_number: int = Field(
        ..., ge=1, description="1-indexed document page number where the field was discovered"
    )


class DocumentMetadata(BaseModel):
    """Metadata describing the processed document container."""
    filename: str
    file_size_bytes: int
    page_count: int
    has_digital_text: bool
    is_encrypted: bool = False
    parser_version: str = "0.1.0"


class ExtractionResult(BaseModel):
    """Complete, structured extraction envelope returned by the library and CLI."""
    status: ExtractionStatus
    document_type: DocumentType
    metadata: DocumentMetadata
    fields: Dict[str, ExtractedField] = Field(default_factory=dict)
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Standard fields expected for this document type that could not be detected"
    )
    raw_text_by_page: Dict[int, str] = Field(
        default_factory=dict,
        description="Raw extracted plain text indexed by 1-based page number"
    )
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None

    def get_field_value(self, key: str, default: Any = None) -> Any:
        """Helper to quickly access a parsed field value."""
        field = self.fields.get(key)
        return field.value if field is not None else default

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to a clean standard Python dictionary."""
        return self.model_dump(mode="json")

    def to_json(self, indent: int = 2) -> str:
        """Serialize result to formatted JSON string."""
        return self.model_dump_json(indent=indent)


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class DocumentExtractionError(Exception):
    """Base exception for all document extraction errors."""
    pass


class InvalidPDFError(DocumentExtractionError):
    """Raised when the input file is not a valid or readable PDF."""
    pass


class EncryptedPDFError(DocumentExtractionError):
    """Raised when the PDF file is password protected and cannot be opened."""
    pass


class EmptyDocumentError(DocumentExtractionError):
    """Raised when the document contains 0 pages or no readable content."""
    pass


class UnsupportedFileFormatError(DocumentExtractionError):
    """Raised when the input file does not match expected PDF format."""
    pass
