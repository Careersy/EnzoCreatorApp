"""Metadata extraction and enrichment helpers."""

from __future__ import annotations

from typing import Any


def detect_platform(text: str, fallback: str | None = None) -> str:
    lower = text.lower()
    if "linkedin" in lower or "comment" in lower and "post" in lower:
        return "LinkedIn"
    if "substack" in lower:
        return "Substack"
    if "newsletter" in lower:
        return "Newsletter"
    if "blog" in lower or "article" in lower:
        return "Blog"
    return fallback or "LinkedIn"


def detect_content_type(text: str, fallback: str | None = None) -> str:
    lower = text.lower()
    if "newsletter" in lower:
        return "newsletter"
    if "blog" in lower:
        return "blog"
    if "article" in lower:
        return "article"
    if len(text.split()) > 500:
        return "long_form"
    return fallback or "post"


def coerce_source_flags(author_type: str, status: str) -> dict[str, bool]:
    author = author_type.lower().strip()
    status_val = status.lower().strip()
    return {
        "is_mine": author == "mine",
        "is_creator_sample": author == "creator",
        "is_draft": status_val == "draft",
        "is_published": status_val == "published",
    }


def build_metadata(
    title: str,
    source_type: str,
    author_type: str,
    platform: str,
    content_type: str,
    tags: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "source_type": source_type,
        "author_type": author_type,
        "platform": platform,
        "content_type": content_type,
        "tags": tags or [],
        "extra": extra or {},
    }
