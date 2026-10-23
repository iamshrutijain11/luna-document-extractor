"""PyMuPDF-based text and structure extraction from PDF files."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union
import fitz  # PyMuPDF

from luna_document_extractor.schemas import (
    DocumentMetadata,
    EmptyDocumentError,
    EncryptedPDFError,
    InvalidPDFError,
)


@dataclass
class ExtractedDocument:
    """Internal container for raw extracted document text and low-level metadata."""
    filename: str
    file_size_bytes: int
    page_count: int
    raw_text_by_page: Dict[int, str]
    has_digital_text: bool
    is_encrypted: bool = False
    is_scanned: bool = False
    warnings: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Concatenated text of all pages separated by newlines."""
        return "\n\n".join(self.raw_text_by_page.values())

    @property
    def total_characters(self) -> int:
        return sum(len(text) for text in self.raw_text_by_page.values())

    def to_metadata(self) -> DocumentMetadata:
        return DocumentMetadata(
            filename=self.filename,
            file_size_bytes=self.file_size_bytes,
            page_count=self.page_count,
            has_digital_text=self.has_digital_text,
            is_encrypted=self.is_encrypted,
        )


class PDFTextExtractor:
    """Extracts text content and layout structures from PDF files using PyMuPDF."""

    def __init__(self, min_char_threshold: int = 30):
        self.min_char_threshold = min_char_threshold

    def extract(self, source: Union[str, Path, bytes], filename: Optional[str] = None) -> ExtractedDocument:
        """Extract text from a file path or in-memory byte buffer.

        Args:
            source: File path (str or Path) or raw PDF bytes.
            filename: Optional filename hint when source is bytes.

        Returns:
            ExtractedDocument containing page-by-page text and extraction status.

        Raises:
            InvalidPDFError: If file is not a valid PDF or is unreadable.
            EncryptedPDFError: If PDF is password-protected and cannot be decrypted.
            EmptyDocumentError: If PDF has zero pages.
        """
        doc: Optional[fitz.Document] = None
        file_size_bytes: int = 0
        resolved_name: str = "document.pdf"
        warnings: List[str] = []

        try:
            if isinstance(source, (str, Path)):
                path_obj = Path(source)
                if not path_obj.exists():
                    raise InvalidPDFError(f"File not found: '{source}'")
                if not path_obj.is_file():
                    raise InvalidPDFError(f"Path is not a regular file: '{source}'")

                file_size_bytes = path_obj.stat().st_size
                resolved_name = path_obj.name

                if file_size_bytes == 0:
                    raise EmptyDocumentError(f"File is empty (0 bytes): '{source}'")

                try:
                    doc = fitz.open(str(path_obj))
                except Exception as exc:
                    raise InvalidPDFError(f"Failed to open PDF '{source}': {exc}") from exc

            elif isinstance(source, bytes):
                file_size_bytes = len(source)
                resolved_name = filename or "stream.pdf"

                if file_size_bytes == 0:
                    raise EmptyDocumentError("Input byte stream is empty (0 bytes).")

                try:
                    doc = fitz.open(stream=source, filetype="pdf")
                except Exception as exc:
                    raise InvalidPDFError(f"Failed to parse PDF byte stream: {exc}") from exc
            else:
                raise InvalidPDFError(f"Unsupported source type: {type(source).__name__}")

            # 1. Check for Encryption
            if doc.is_encrypted:
                # Try empty password default
                if not doc.authenticate(""):
                    raise EncryptedPDFError(
                        f"PDF '{resolved_name}' is password-protected and cannot be extracted."
                    )

            # 2. Check Page Count
            page_count = len(doc)
            if page_count == 0:
                raise EmptyDocumentError(f"PDF '{resolved_name}' has 0 pages.")

            # 3. Extract Text Page-by-Page
            raw_text_by_page: Dict[int, str] = {}
            total_images = 0

            for page_idx in range(page_count):
                page_num = page_idx + 1
                page = doc[page_idx]
                page_text = page.get_text("text") or ""
                raw_text_by_page[page_num] = page_text
                total_images += len(page.get_images())

            total_chars = sum(len(txt.strip()) for txt in raw_text_by_page.values())

            # 4. Check for Scanned / Image-Only PDF
            has_digital_text = True
            is_scanned = False

            if total_chars < self.min_char_threshold:
                has_digital_text = False
                if total_images > 0:
                    is_scanned = True
                    warnings.append(
                        "Document appears to be a scanned image or photo PDF. "
                        "Offline OCR is not supported; extracted text layer is empty."
                    )
                else:
                    warnings.append(
                        "Document contains zero or minimal digital text content."
                    )

            return ExtractedDocument(
                filename=resolved_name,
                file_size_bytes=file_size_bytes,
                page_count=page_count,
                raw_text_by_page=raw_text_by_page,
                has_digital_text=has_digital_text,
                is_encrypted=doc.is_encrypted,
                is_scanned=is_scanned,
                warnings=warnings,
            )

        finally:
            if doc is not None:
                doc.close()
