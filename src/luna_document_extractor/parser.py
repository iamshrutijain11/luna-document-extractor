"""Document classification, field parsing, and deterministic fact extraction."""

import re
from typing import Dict, List, Optional, Set, Tuple

from luna_document_extractor.extractor import ExtractedDocument
from luna_document_extractor.patterns import (
    CLAIM_REQUIREMENTS_PATTERNS,
    COVERAGE_SCOPE_PATTERNS,
    CUSTOMER_PATTERNS,
    DATE_PATTERNS,
    EXCLUSIONS_PATTERNS,
    INVOICE_ID_PATTERNS,
    PRODUCT_PATTERNS,
    RECEIPT_ID_PATTERNS,
    SERIAL_NUMBER_PATTERNS,
    SUBTOTAL_PATTERNS,
    TAX_PATTERNS,
    TOTAL_AMOUNT_PATTERNS,
    WARRANTY_TERM_PATTERNS,
    detect_currency,
    normalize_amount,
    normalize_date,
)
from luna_document_extractor.schemas import (
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)


class DocumentParser:
    """Classifies document types and extracts candidate structured fields."""

    # Required key fields by document type
    REQUIRED_FIELDS: Dict[DocumentType, List[str]] = {
        DocumentType.INVOICE: ["invoice_number", "total_amount", "invoice_date"],
        DocumentType.RECEIPT: ["total_amount", "receipt_date"],
        DocumentType.WARRANTY: ["warranty_term"],
        DocumentType.UNKNOWN: ["date", "total_amount"],
    }

    def __init__(self, document_type_hint: Optional[DocumentType] = None):
        self.type_hint = document_type_hint

    def parse(self, doc: ExtractedDocument) -> ExtractionResult:
        """Parse an extracted PDF document into structured fields.

        Args:
            doc: ExtractedDocument object containing text by page.

        Returns:
            ExtractionResult containing detected fields, status, and missing requirements.
        """
        metadata = doc.to_metadata()
        warnings = list(doc.warnings)

        # 1. Handle Empty or Scanned Documents
        if not doc.has_digital_text:
            status = ExtractionStatus.NEEDS_OCR if doc.is_scanned else ExtractionStatus.EMPTY
            return ExtractionResult(
                status=status,
                document_type=DocumentType.UNKNOWN,
                metadata=metadata,
                fields={},
                missing_fields=[],
                raw_text_by_page=doc.raw_text_by_page,
                warnings=warnings,
            )

        # 2. Classify Document Type
        doc_type = self.type_hint or self.classify(doc.full_text)

        # 3. Extract Fields by Page
        fields: Dict[str, ExtractedField] = {}

        # Universal extraction (Dates, Amounts, Currency, Vendor/Merchant)
        self._extract_dates(doc, fields, doc_type)
        self._extract_monetary(doc, fields)
        self._extract_vendor(doc, fields)

        # Domain-specific extraction
        if doc_type == DocumentType.INVOICE:
            self._extract_invoice_fields(doc, fields)
        elif doc_type == DocumentType.RECEIPT:
            self._extract_receipt_fields(doc, fields)
        elif doc_type == DocumentType.WARRANTY:
            self._extract_warranty_fields(doc, fields)
        else:
            # For unknown, attempt all pattern groups
            self._extract_invoice_fields(doc, fields)
            self._extract_warranty_fields(doc, fields)

        # 4. Determine Missing Fields
        expected = self.REQUIRED_FIELDS.get(doc_type, [])
        missing = [key for key in expected if key not in fields]

        # 5. Assess Extraction Status
        if len(fields) == 0:
            status = ExtractionStatus.PARTIAL
        elif len(missing) == 0:
            status = ExtractionStatus.SUCCESS
        else:
            status = ExtractionStatus.PARTIAL

        return ExtractionResult(
            status=status,
            document_type=doc_type,
            metadata=metadata,
            fields=fields,
            missing_fields=missing,
            raw_text_by_page=doc.raw_text_by_page,
            warnings=warnings,
        )

    def classify(self, text: str) -> DocumentType:
        """Classify document type based on keyword frequency and semantic cues."""
        lower_text = text.lower()

        scores = {
            DocumentType.INVOICE: 0,
            DocumentType.RECEIPT: 0,
            DocumentType.WARRANTY: 0,
        }

        # Invoice signals
        invoice_keywords = [
            ("invoice", 3), ("bill to", 3), ("invoice number", 4),
            ("due date", 3), ("remit to", 3), ("tax invoice", 4),
            ("balance due", 3), ("subtotal", 2), ("net amount", 2)
        ]
        for kw, weight in invoice_keywords:
            if kw in lower_text:
                scores[DocumentType.INVOICE] += weight

        # Receipt signals
        receipt_keywords = [
            ("receipt", 4), ("sales receipt", 4), ("cashier", 3),
            ("store #", 3), ("register #", 3), ("change due", 4),
            ("tender", 2), ("merchant", 2), ("thank you for your business", 2)
        ]
        for kw, weight in receipt_keywords:
            if kw in lower_text:
                scores[DocumentType.RECEIPT] += weight

        # Warranty signals
        warranty_keywords = [
            ("warranty", 5), ("limited warranty", 5), ("guarantee", 4),
            ("coverage", 3), ("exclusions", 4), ("claim procedure", 4),
            ("does not cover", 4), ("hardware warranty", 5), ("serial number", 3)
        ]
        for kw, weight in warranty_keywords:
            if kw in lower_text:
                scores[DocumentType.WARRANTY] += weight

        # Find category with highest positive score
        best_type, max_score = max(scores.items(), key=lambda item: item[1])
        if max_score >= 3:
            return best_type
        return DocumentType.UNKNOWN

    # ─────────────────────────────────────────────────────────────────────────
    # Field Extractors
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_dates(self, doc: ExtractedDocument, fields: Dict[str, ExtractedField], doc_type: DocumentType) -> None:
        """Detect and normalize dates across all pages."""
        date_key = "invoice_date" if doc_type == DocumentType.INVOICE else (
            "receipt_date" if doc_type == DocumentType.RECEIPT else (
                "purchase_date" if doc_type == DocumentType.WARRANTY else "date"
            )
        )

        for page_num, text in doc.raw_text_by_page.items():
            lines = text.splitlines()
            for line in lines:
                lower_line = line.lower()
                # Check for anchored date (e.g. "Invoice Date: 2025-06-15")
                is_anchored = any(k in lower_line for k in ["date:", "dated", "issued:", "invoice date", "purchase date"])
                is_due_date = "due" in lower_line

                for pattern, fmt_type in DATE_PATTERNS:
                    match = pattern.search(line)
                    if match:
                        norm = normalize_date(match.groups(), fmt_type)
                        conf = 0.96 if is_anchored else 0.75

                        if is_due_date and "due_date" not in fields:
                            fields["due_date"] = ExtractedField(
                                key="due_date",
                                value=norm,
                                confidence=0.95,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                        elif date_key not in fields:
                            fields[date_key] = ExtractedField(
                                key=date_key,
                                value=norm,
                                confidence=conf,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                        break

    def _extract_monetary(self, doc: ExtractedDocument, fields: Dict[str, ExtractedField]) -> None:
        """Detect total amount, subtotal, tax, and currency."""
        # Currency
        currency = detect_currency(doc.full_text)
        fields["currency"] = ExtractedField(
            key="currency",
            value=currency,
            confidence=0.90,
            raw_text=currency,
            page_number=1,
        )

        for page_num, text in doc.raw_text_by_page.items():
            lines = text.splitlines()
            for line in lines:
                # 1. Total Amount
                if "total_amount" not in fields:
                    for pat in TOTAL_AMOUNT_PATTERNS:
                        m = pat.search(line)
                        if m:
                            amt = normalize_amount(m.group(1))
                            if amt is not None:
                                fields["total_amount"] = ExtractedField(
                                    key="total_amount",
                                    value=amt,
                                    confidence=0.98,
                                    raw_text=line.strip(),
                                    page_number=page_num,
                                )
                                break

                # 2. Subtotal
                if "subtotal" not in fields:
                    for pat in SUBTOTAL_PATTERNS:
                        m = pat.search(line)
                        if m:
                            amt = normalize_amount(m.group(1))
                            if amt is not None:
                                fields["subtotal"] = ExtractedField(
                                    key="subtotal",
                                    value=amt,
                                    confidence=0.95,
                                    raw_text=line.strip(),
                                    page_number=page_num,
                                )
                                break

                # 3. Tax
                if "tax_amount" not in fields:
                    for pat in TAX_PATTERNS:
                        m = pat.search(line)
                        if m:
                            amt = normalize_amount(m.group(1))
                            if amt is not None:
                                fields["tax_amount"] = ExtractedField(
                                    key="tax_amount",
                                    value=amt,
                                    confidence=0.95,
                                    raw_text=line.strip(),
                                    page_number=page_num,
                                )
                                break

    def _extract_vendor(self, doc: ExtractedDocument, fields: Dict[str, ExtractedField]) -> None:
        """Extract vendor, merchant, or seller name from top headers."""
        page_1_text = doc.raw_text_by_page.get(1, "")
        lines = [line.strip() for line in page_1_text.splitlines() if line.strip()]

        # Heuristic: First 1-3 lines that contain company indicator or title
        company_indicators = ["inc", "llc", "ltd", "corp", "corporation", "technologies", "services", "solutions", "store", "direct", "retail", "electric", "power", "energy"]
        for idx, line in enumerate(lines[:6]):
            # Skip common generic headings
            if line.lower() in ["invoice", "receipt", "warranty", "tax invoice"]:
                continue
            if any(ind in line.lower() for ind in company_indicators) or (idx == 0 and len(line) > 3):
                fields["vendor_name"] = ExtractedField(
                    key="vendor_name",
                    value=line,
                    confidence=0.85 if any(ind in line.lower() for ind in company_indicators) else 0.70,
                    raw_text=line,
                    page_number=1,
                )
                break

    def _extract_invoice_fields(self, doc: ExtractedDocument, fields: Dict[str, ExtractedField]) -> None:
        """Extract invoice-specific fields (invoice number, customer/bill to)."""
        for page_num, text in doc.raw_text_by_page.items():
            lines = text.splitlines()
            for line in lines:
                # Invoice ID
                if "invoice_number" not in fields:
                    for pat in INVOICE_ID_PATTERNS:
                        m = pat.search(line)
                        if m:
                            fields["invoice_number"] = ExtractedField(
                                key="invoice_number",
                                value=m.group(1).strip(),
                                confidence=0.98,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                            break

                # Customer Name
                if "customer_name" not in fields:
                    for pat in CUSTOMER_PATTERNS:
                        m = pat.search(line)
                        if m:
                            cust = m.group(1).strip()
                            if len(cust) > 2:
                                fields["customer_name"] = ExtractedField(
                                    key="customer_name",
                                    value=cust,
                                    confidence=0.92,
                                    raw_text=line.strip(),
                                    page_number=page_num,
                                )
                                break

    def _extract_receipt_fields(self, doc: ExtractedDocument, fields: Dict[str, ExtractedField]) -> None:
        """Extract receipt-specific fields (receipt/order number)."""
        for page_num, text in doc.raw_text_by_page.items():
            lines = text.splitlines()
            for line in lines:
                if "receipt_number" not in fields:
                    for pat in RECEIPT_ID_PATTERNS:
                        m = pat.search(line)
                        if m:
                            fields["receipt_number"] = ExtractedField(
                                key="receipt_number",
                                value=m.group(1).strip(),
                                confidence=0.96,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                            break

    def _extract_warranty_fields(self, doc: ExtractedDocument, fields: Dict[str, ExtractedField]) -> None:
        """Extract warranty terms, coverage, exclusions, serial numbers, and product."""
        for page_num, text in doc.raw_text_by_page.items():
            lines = text.splitlines()
            for line in lines:
                # 1. Warranty Term / Duration
                if "warranty_term" not in fields:
                    for pat in WARRANTY_TERM_PATTERNS:
                        m = pat.search(line)
                        if m:
                            fields["warranty_term"] = ExtractedField(
                                key="warranty_term",
                                value=m.group(1).strip(),
                                confidence=0.95,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                            break

                # 2. Serial Number
                if "serial_number" not in fields:
                    for pat in SERIAL_NUMBER_PATTERNS:
                        m = pat.search(line)
                        if m:
                            fields["serial_number"] = ExtractedField(
                                key="serial_number",
                                value=m.group(1).strip(),
                                confidence=0.97,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                            break

                # 3. Product Name
                if "product_name" not in fields:
                    for pat in PRODUCT_PATTERNS:
                        m = pat.search(line)
                        if m:
                            prod = m.group(1).strip()
                            if len(prod) > 2:
                                fields["product_name"] = ExtractedField(
                                    key="product_name",
                                    value=prod,
                                    confidence=0.92,
                                    raw_text=line.strip(),
                                    page_number=page_num,
                                )
                                break

                # 4. Coverage Scope
                if "coverage_scope" not in fields:
                    for pat in COVERAGE_SCOPE_PATTERNS:
                        m = pat.search(line)
                        if m:
                            fields["coverage_scope"] = ExtractedField(
                                key="coverage_scope",
                                value=m.group(1).strip(),
                                confidence=0.90,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                            break

                # 5. Exclusions
                if "exclusions" not in fields:
                    for pat in EXCLUSIONS_PATTERNS:
                        m = pat.search(line)
                        if m:
                            fields["exclusions"] = ExtractedField(
                                key="exclusions",
                                value=m.group(1).strip(),
                                confidence=0.90,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                            break

                # 6. Claim Requirements
                if "claim_requirements" not in fields:
                    for pat in CLAIM_REQUIREMENTS_PATTERNS:
                        m = pat.search(line)
                        if m:
                            fields["claim_requirements"] = ExtractedField(
                                key="claim_requirements",
                                value=m.group(1).strip(),
                                confidence=0.92,
                                raw_text=line.strip(),
                                page_number=page_num,
                            )
                            break
