"""Text ingestion helpers for files and pasted content."""

from __future__ import annotations

from pathlib import Path

from creator_intelligence_app.ingestion.pdf_parser import PDFParserError, extract_pdf_text


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)

    if suffix in {".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".html"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    # best effort fallback for other text-like files
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:  # pragma: no cover
        raise PDFParserError(f"Unsupported file type for ingestion: {suffix}") from exc
