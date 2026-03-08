"""Chunking utilities for ingestion pipeline."""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def chunk_text(text: str, max_words: int = 140) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    chunks: list[str] = []

    for paragraph in paragraphs:
        words = paragraph.split()
        if len(words) <= max_words:
            chunks.append(paragraph)
            continue

        start = 0
        while start < len(words):
            part = words[start : start + max_words]
            chunks.append(" ".join(part))
            start += max_words

    return chunks


def token_estimate(text: str) -> int:
    # practical heuristic for local estimates
    return max(1, int(len(text) / 4))
