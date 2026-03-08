"""PDF parsing with optional dependency fallback."""

from __future__ import annotations

from pathlib import Path

try:
    from pypdf import PdfReader  # type: ignore
except ImportError:  # pragma: no cover
    PdfReader = None


class PDFParserError(RuntimeError):
    pass


def extract_pdf_text(file_path: Path) -> str:
    if PdfReader is None:
        raise PDFParserError(
            "pypdf is not installed. Install dependencies to enable PDF ingestion."
        )

    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages).strip()
