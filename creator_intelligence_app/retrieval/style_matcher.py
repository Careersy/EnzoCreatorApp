"""Retrieve user examples that best match style intent."""

from __future__ import annotations

from collections import Counter
from typing import Any

from creator_intelligence_app.app.db.database import Database


class StyleMatcher:
    def __init__(self, db: Database) -> None:
        self.db = db

    @staticmethod
    def _text_signature(text: str) -> dict[str, float]:
        words = text.split()
        sentence_count = max(1, text.count(".") + text.count("!") + text.count("?"))
        avg_sentence_len = len(words) / sentence_count
        q_ratio = text.count("?") / sentence_count
        you_ratio = text.lower().split().count("you") / max(1, len(words))
        return {
            "avg_sentence_len": avg_sentence_len,
            "q_ratio": q_ratio,
            "you_ratio": you_ratio,
        }

    @staticmethod
    def _distance(a: dict[str, float], b: dict[str, float]) -> float:
        keys = set(a.keys()) | set(b.keys())
        return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)

    def top_matching_user_examples(self, reference_text: str, limit: int = 5) -> list[dict[str, Any]]:
        chunks = self.db.get_chunks(author_type="mine", limit=600)
        if not chunks:
            return []

        ref_sig = self._text_signature(reference_text)
        ranked = []
        for item in chunks:
            txt = str(item.get("chunk_text", ""))
            if not txt.strip():
                continue
            sig = self._text_signature(txt)
            dist = self._distance(ref_sig, sig)
            ranked.append(
                {
                    "chunk_id": item.get("id"),
                    "source_id": item.get("source_id"),
                    "text": txt,
                    "distance": round(dist, 4),
                }
            )

        ranked.sort(key=lambda x: x["distance"])
        return ranked[:limit]

    def preferred_phrases(self, limit: int = 12) -> list[str]:
        rows = self.db.list_phrase_rules(rule_type="preferred") + self.db.list_phrase_rules(rule_type="signature")
        phrases = [str(r["phrase"]) for r in rows]
        if phrases:
            return phrases[:limit]

        texts = self.db.get_source_texts(is_mine=True, limit=120)
        counter = Counter()
        for text in texts:
            words = [w.strip(".,!?;:\"'()[]").lower() for w in text.split()]
            words = [w for w in words if len(w) > 3]
            for i in range(len(words) - 1):
                counter[f"{words[i]} {words[i+1]}"] += 1
        return [phrase for phrase, _count in counter.most_common(limit)]

    def banned_phrases(self) -> list[str]:
        return [str(r["phrase"]) for r in self.db.list_phrase_rules(rule_type="banned")]

    def overused_phrases(self) -> list[str]:
        return [str(r["phrase"]) for r in self.db.list_phrase_rules(rule_type="overused")]
