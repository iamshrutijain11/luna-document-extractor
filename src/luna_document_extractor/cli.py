"""Command-line interface (CLI) for Luna Document Extractor."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from luna_document_extractor.extractor import PDFTextExtractor
from luna_document_extractor.parser import DocumentParser
from luna_document_extractor.schemas import (
    DocumentExtractionError,
    DocumentType,
    EncryptedPDFError,
    InvalidPDFError,
)

__version__ = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="luna-extract",
        description="Luna Document Extractor — Offline PDF extractor and parser for invoices, receipts, and warranties.",
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF document to extract",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Optional destination file to write JSON results (default: stdout)",
    )
    parser.add_argument(
        "--doc-type",
        type=str,
        choices=["invoice", "receipt", "warranty", "auto"],
        default="auto",
        help="Hint for document classification (default: auto)",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Output raw extracted plain text rather than structured JSON",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output single-line compact JSON without indentation",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed diagnostic logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    pdf_file = Path(args.pdf_path)

    # Validate document type hint
    type_hint = None
    if args.doc_type != "auto":
        type_hint = DocumentType(args.doc_type)

    extractor = PDFTextExtractor()
    doc_parser = DocumentParser(document_type_hint=type_hint)

    try:
        # Extract low-level PDF text
        doc = extractor.extract(pdf_file)

        # Plain text mode shortcut
        if args.text_only:
            output_content = doc.full_text
        else:
            # Parse structured fields
            result = doc_parser.parse(doc)
            indent = None if args.compact else 2
            output_content = result.to_json(indent=indent)

        # Output routing
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output_content, encoding="utf-8")
            if args.verbose:
                print(f"[Luna Extractor] Output written to '{out_path}'", file=sys.stderr)
        else:
            print(output_content)

        return 0

    except EncryptedPDFError as err:
        print(f"Error: Password-protected PDF — {err}", file=sys.stderr)
        return 1

    except InvalidPDFError as err:
        print(f"Error: Invalid or corrupt PDF — {err}", file=sys.stderr)
        return 1

    except DocumentExtractionError as err:
        print(f"Error: Extraction failure — {err}", file=sys.stderr)
        return 1

    except Exception as exc:
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
