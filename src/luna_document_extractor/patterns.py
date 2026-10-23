"""Regular expressions, anchored patterns, and extraction heuristics."""

import re
from typing import Dict, List, Optional, Pattern, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Regex Patterns
# ─────────────────────────────────────────────────────────────────────────────

# Currency Symbols and ISO codes
CURRENCY_PATTERN: Pattern = re.compile(r"(\$|€|£|₹|USD|EUR|GBP|INR|CAD|AUD)\s*")

# Monetary amounts with optional currency symbol: $1,234.56 or 1234.56 or 1,234.00
AMOUNT_VALUE_REGEX = r"(?:\$|€|£|₹|USD|EUR|GBP|INR)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+(?:\.[0-9]{2}))"

# Dates: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, or Month DD, YYYY
DATE_PATTERNS: List[Tuple[Pattern, str]] = [
    # ISO 8601: 2025-06-15 or 2025/06/15
    (re.compile(r"\b(20[2-9][0-9])[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01])\b"), "YYYY-MM-DD"),
    # Month DD, YYYY: June 15, 2025 or 15 June 2025
    (re.compile(
        r"\b(?:(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+([0-9]{1,2})(?:st|nd|rd|th)?,?\s+(20[2-9][0-9]))\b",
        re.IGNORECASE
    ), "MONTH_DD_YYYY"),
    (re.compile(
        r"\b(?:([0-9]{1,2})(?:st|nd|rd|th)?\s+"
        r"(January|February|March|April|May|June|July|August|September|October|November|December),?\s+"
        r"(20[2-9][0-9]))\b",
        re.IGNORECASE
    ), "DD_MONTH_YYYY"),
    # MM/DD/YYYY or DD/MM/YYYY
    (re.compile(r"\b(0[1-9]|1[0-2]|[1-9])/(0[1-9]|[12][0-9]|3[01]|[1-9])/(20[2-9][0-9])\b"), "MM/DD/YYYY"),
]

# Anchored Invoice Identifier Patterns
INVOICE_ID_PATTERNS: List[Pattern] = [
    # Require at least one digit to avoid capturing generic words like "has"
    re.compile(r"(?:invoice\s*(?:number|no|#|id)?|bill\s*(?:no|#)?)\s*[:.\-]?\s*(?=.*\d)([A-Z0-9\-_]{3,30})\b", re.IGNORECASE),
    re.compile(r"\b(INV[-_]?[0-9]{3,12}[A-Z0-9\-]*)\b", re.IGNORECASE),
]

# Anchored Receipt Identifier Patterns
RECEIPT_ID_PATTERNS: List[Pattern] = [
    re.compile(r"(?:receipt\s*(?:number|no|#|id)?|ticket\s*(?:no|#)?|order\s*(?:number|no|#|id)?)\s*[:.\-]?\s*([A-Z0-9\-_]{3,30})\b", re.IGNORECASE),
    re.compile(r"(?:transaction\s*(?:id|#|no)?)\s*[:.\-]?\s*([A-Z0-9\-_]{3,30})\b", re.IGNORECASE),
]

# Anchored Total Amount Patterns (avoid matching subtotal lines)
TOTAL_AMOUNT_PATTERNS: List[Pattern] = [
    # Specific phrases that denote the final total
    re.compile(r"(?:total\s+amount\s+due|total\s+amount\s+paid|grand\s*total|balance\s*due|amount\s+due|net\s*total)\s*[:.\-]?\s*" + AMOUNT_VALUE_REGEX, re.IGNORECASE),
    # Simple "Total" lines that are not preceded by "sub" (negative lookbehind)
    re.compile(r"(?<!sub)total\s*[:.\-]?\s*" + AMOUNT_VALUE_REGEX, re.IGNORECASE),
]

# Subtotal & Tax Patterns
SUBTOTAL_PATTERNS: List[Pattern] = [
    re.compile(r"(?:subtotal|sub-total|net\s*amount)\s*[:.\-]?\s*" + AMOUNT_VALUE_REGEX, re.IGNORECASE),
]

TAX_PATTERNS: List[Pattern] = [
    re.compile(r"(?:tax|vat|gst|sales\s*tax)\s*(?:\([0-9.]+%\))?\s*[:.\-]?\s*" + AMOUNT_VALUE_REGEX, re.IGNORECASE),
]

# Serial Number Patterns
SERIAL_NUMBER_PATTERNS: List[Pattern] = [
    re.compile(r"(?:serial\s*(?:number|no|#)?|s/n\b|sn\b)\s*[:.\-]?\s*([A-Z0-9\-_]{4,35})\b", re.IGNORECASE),
    re.compile(r"\b(SN-[A-Z0-9\-_]{4,25})\b", re.IGNORECASE),
]

# Warranty Duration / Term Patterns
WARRANTY_TERM_PATTERNS: List[Pattern] = [
    re.compile(r"(?:warranty\s*(?:period|duration|term|length)?|coverage\s*(?:period)?)\s*[:.\-]?\s*([^\n\r,;.]{3,60})", re.IGNORECASE),
    re.compile(r"\b([0-9]+\s*(?:year|yr|month|mo)s?\s*(?:limited|standard|hardware|basic)?\s*warranty)\b", re.IGNORECASE),
    re.compile(r"\b(1-year|2-year|3-year|5-year)\s*(?:basic|limited|hardware)?\s*warranty\b", re.IGNORECASE),
    re.compile(r"\b(lifetime\s*warranty)\b", re.IGNORECASE),
]

# Customer / Bill To Patterns
CUSTOMER_PATTERNS: List[Pattern] = [
    re.compile(r"(?:bill\s*to|sold\s*to|customer|buyer|client)\s*[:.\-]?\s*([A-Z][A-Za-z\s.\-]{2,40})", re.IGNORECASE),
]

# Product / Item Patterns
PRODUCT_PATTERNS: List[Pattern] = [
    re.compile(r"(?:product(?:\s*name)?|item(?:\s*description)?|device|model|equipment)\s*[:.\-]?\s*([A-Z0-9][A-Za-z0-9\s.\-_/()]{2,60})", re.IGNORECASE),
]

# Coverage & Exclusions Patterns
COVERAGE_SCOPE_PATTERNS: List[Pattern] = [
    re.compile(r"(?:covers|coverage\s*scope|covered\s*items)\s*[:.\-]?\s*([^\n\r]{10,200})", re.IGNORECASE),
]

EXCLUSIONS_PATTERNS: List[Pattern] = [
    re.compile(r"(?:exclusions|not\s*covered|does\s*not\s*cover)\s*[:.\-]?\s*([^\n\r]{10,200})", re.IGNORECASE),
]

CLAIM_REQUIREMENTS_PATTERNS: List[Pattern] = [
    re.compile(r"(?:required\s*for\s*claim|claim\s*requirements|how\s*to\s*claim)\s*[:.\-]?\s*([^\n\r]{10,200})", re.IGNORECASE),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

MONTH_NAMES: Dict[str, str] = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12"
}


def normalize_amount(raw_str: str) -> Optional[float]:
    """Clean a string amount to a float value."""
    try:
        cleaned = re.sub(r"[^\d.]", "", raw_str)
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def normalize_date(match_groups: Tuple[str, ...], fmt_type: str) -> str:
    """Normalize extracted date parts into canonical ISO YYYY-MM-DD."""
    if fmt_type == "YYYY-MM-DD":
        return f"{match_groups[0]}-{int(match_groups[1]):02d}-{int(match_groups[2]):02d}"
    elif fmt_type == "MONTH_DD_YYYY":
        month = MONTH_NAMES.get(match_groups[0].lower(), "01")
        return f"{match_groups[2]}-{month}-{int(match_groups[1]):02d}"
    elif fmt_type == "DD_MONTH_YYYY":
        month = MONTH_NAMES.get(match_groups[1].lower(), "01")
        return f"{match_groups[2]}-{month}-{int(match_groups[0]):02d}"
    elif fmt_type == "MM/DD/YYYY":
        # standard MM/DD/YYYY
        return f"{match_groups[2]}-{int(match_groups[0]):02d}-{int(match_groups[1]):02d}"
    return "".join(match_groups)


def detect_currency(text: str) -> str:
    """Detect primary currency symbol or code in text."""
    if "$" in text or "USD" in text:
        return "USD"
    if "€" in text or "EUR" in text:
        return "EUR"
    if "£" in text or "GBP" in text:
        return "GBP"
    if "₹" in text or "INR" in text:
        return "INR"
    return "USD"  # default standard
