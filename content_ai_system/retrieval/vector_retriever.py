"""Optional vector retrieval for unstructured creator content."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class VectorDocument:
    text: str
    metadata: dict[str, str]
    embedding: list[float]


class LocalVectorRetriever:
    """Simple in-memory vector index for demo and local development."""

    def __init__(self) -> None:
        self.documents: list[VectorDocument] = []

    def _embed(self, text: str) -> list[float]:
        # Lightweight deterministic embedding to avoid external dependency in scaffold.
        buckets = [0.0] * 16
        for token in text.lower().split():
            idx = hash(token) % len(buckets)
            buckets[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in buckets)) or 1.0
        return [v / norm for v in buckets]

    def add_document(self, text: str, metadata: dict[str, str] | None = None) -> None:
        self.documents.append(
            VectorDocument(text=text, metadata=metadata or {}, embedding=self._embed(text))
        )

    def similarity_search(self, query: str, k: int = 5) -> list[str]:
        if not self.documents:
            return []

        q = self._embed(query)

        def score(doc: VectorDocument) -> float:
            return sum(a * b for a, b in zip(q, doc.embedding))

        ranked = sorted(self.documents, key=score, reverse=True)
        return [doc.text for doc in ranked[:k]]
