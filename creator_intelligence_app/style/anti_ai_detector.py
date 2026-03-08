"""Rule-based detector for generic AI phrasing risk."""

from __future__ import annotations

import re
from typing import Any


DEFAULT_GENERIC_PHRASES = [
    "in today's fast-paced world",
    "unlock your potential",
    "game changer",
    "delve into",
    "in conclusion",
    "it's important to note",
    "seamlessly",
    "robust",
    "leverage",
    "ever-evolving",
    "in this article",
    "let's dive in",
    "at the end of the day",
    "without further ado",
]


class AntiAIDetector:
    def __init__(self, generic_phrases: list[str] | None = None) -> None:
        self.generic_phrases = generic_phrases or DEFAULT_GENERIC_PHRASES

    def evaluate(self, text: str, banned_phrases: list[str] | None = None) -> dict[str, Any]:
        lower = text.lower()
        generic_hits = [phrase for phrase in self.generic_phrases if phrase in lower]
        banned_hits = [phrase for phrase in (banned_phrases or []) if phrase.lower() in lower]

        sentence_count = max(1, text.count(".") + text.count("!") + text.count("?"))
        avg_len = len(text.split()) / sentence_count

        risk = 0.0
        risk += min(0.5, len(generic_hits) * 0.08)
        risk += min(0.3, len(banned_hits) * 0.12)
        if avg_len > 28:
            risk += 0.1
        if "!!!" in text or text.count("!") > sentence_count:
            risk += 0.05
        if lower.count("you ") == 0 and lower.count("your ") == 0:
            risk += 0.05
        if text.count("\n") < 2 and len(text.split()) > 120:
            risk += 0.08

        risk = min(1.0, risk)

        notes = []
        if generic_hits:
            notes.append("Detected generic transition/marketing phrasing.")
        if banned_hits:
            notes.append("Detected user-banned phrases.")
        if avg_len > 28:
            notes.append("Sentences are long and may sound overly polished.")
        if lower.count("you ") == 0 and lower.count("your ") == 0:
            notes.append("Low direct address; draft may feel generic and impersonal.")
        if text.count("\n") < 2 and len(text.split()) > 120:
            notes.append("Paragraph pacing is dense for social-style writing.")

        return {
            "genericity_risk": round(risk * 100, 1),
            "generic_hits": generic_hits,
            "banned_hits": banned_hits,
            "notes": notes,
        }

    def reduce_genericity(
        self,
        text: str,
        banned_phrases: list[str] | None = None,
        preferred_phrases: list[str] | None = None,
    ) -> str:
        out = text
        banned = [p for p in (banned_phrases or []) if p]
        for phrase in banned + self.generic_phrases:
            if not phrase:
                continue
            out = re.sub(re.escape(phrase), "", out, flags=re.IGNORECASE)

        # tighten bloated transitions
        out = re.sub(r"\b(it is important to note that|in order to|as a matter of fact)\b", "", out, flags=re.IGNORECASE)
        out = re.sub(r"\s{2,}", " ", out).strip()

        # add preferred phrase anchors only if present and text is long
        preferred = [p for p in (preferred_phrases or []) if isinstance(p, str) and p.strip()]
        if preferred and len(out.split()) > 80:
            anchor = preferred[0].strip()
            if anchor and anchor.lower() not in out.lower():
                out = f"{anchor}. {out}"

        return out
