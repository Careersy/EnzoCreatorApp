"""Graph query helpers and NL query parsing."""

from __future__ import annotations


def infer_relation_from_query(query: str) -> str:
    q = query.lower()
    if "hook" in q:
        return "USES_TEMPLATE"
    if "cta" in q or "call to action" in q:
        return "HAS_CTA"
    if "platform" in q:
        return "ACTIVE_ON"
    if "topic" in q or "cover" in q:
        return "COVERS"
    return "USES_TEMPLATE"


def extract_topic_hint(query: str) -> str | None:
    q = query.lower()
    markers = ["about", "on", "for"]
    for marker in markers:
        key = f" {marker} "
        if key in q:
            return query[q.index(key) + len(key) :].strip()
    return None
