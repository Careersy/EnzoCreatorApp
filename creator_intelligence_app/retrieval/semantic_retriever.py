"""Local semantic retrieval over ingested chunks."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from creator_intelligence_app.app.config.settings import SETTINGS
from creator_intelligence_app.app.db.database import Database


class SemanticRetriever:
    def __init__(self, db: Database, dim: int = 24) -> None:
        self.db = db
        self.dim = dim
        self.backend = str(SETTINGS.vector_backend or "local").lower()
        self._chroma = None
        self._collection = None
        if self.backend == "chroma":
            self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            chromadb = __import__("chromadb")
            self._chroma = chromadb.PersistentClient(path=SETTINGS.chroma_persist_dir)
            self._collection = self._chroma.get_or_create_collection(
                name="source_chunks",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:  # pragma: no cover
            self._chroma = None
            self._collection = None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        # simple local-first tokenizer with light stopword filtering
        stop = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "in",
            "on",
            "for",
            "is",
            "are",
            "was",
            "were",
            "it",
            "that",
            "this",
            "with",
            "as",
            "by",
            "at",
            "be",
            "from",
            "you",
            "your",
        }
        tokens = re.findall(r"[A-Za-z0-9_']+", text.lower())
        return [t for t in tokens if len(t) > 2 and t not in stop]

    def embed(self, text: str) -> list[float]:
        # fallback dense embedding for compatibility with existing storage
        buckets = [0.0] * self.dim
        for token in text.lower().split():
            buckets[hash(token) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in buckets)) or 1.0
        return [x / norm for x in buckets]

    @staticmethod
    def cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        size = min(len(a), len(b))
        return float(sum(a[i] * b[i] for i in range(size)))

    def search(
        self,
        query: str,
        author_type: str | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        if self._collection is not None:
            chroma_hits = self._search_chroma(
                query=query,
                author_type=author_type,
                platform=platform,
                content_type=content_type,
                limit=limit,
            )
            if chroma_hits:
                return chroma_hits

        rows = self.db.get_chunks(
            author_type=author_type,
            platform=platform,
            content_type=content_type,
            limit=800,
        )
        if not rows:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # corpus document frequencies for local IDF weighting
        doc_freq: Counter[str] = Counter()
        doc_tokens: list[set[str]] = []
        tokenized_docs: list[list[str]] = []
        for row in rows:
            tokens = self._tokenize(str(row.get("chunk_text", "")))
            tokenized_docs.append(tokens)
            uniq = set(tokens)
            doc_tokens.append(uniq)
            for token in uniq:
                doc_freq[token] += 1

        n_docs = len(rows)
        idf: dict[str, float] = {}
        for token, df in doc_freq.items():
            idf[token] = math.log((1 + n_docs) / (1 + df)) + 1.0

        q_tf = Counter(query_tokens)
        q_weights: dict[str, float] = {}
        for token, tf in q_tf.items():
            q_weights[token] = (1.0 + math.log(tf)) * idf.get(token, 1.0)
        q_norm = math.sqrt(sum(v * v for v in q_weights.values())) or 1.0

        q_dense = self.embed(query)
        scored: list[dict[str, object]] = []
        for row, tokens in zip(rows, tokenized_docs):
            tf = Counter(tokens)
            d_weights: dict[str, float] = {}
            for token, freq in tf.items():
                d_weights[token] = (1.0 + math.log(freq)) * idf.get(token, 1.0)
            d_norm = math.sqrt(sum(v * v for v in d_weights.values())) or 1.0

            lexical_dot = 0.0
            for token, w in q_weights.items():
                lexical_dot += w * d_weights.get(token, 0.0)
            lexical_score = lexical_dot / (q_norm * d_norm)

            dense_vec = row.get("embedding") or []
            if not dense_vec:
                dense_vec = self.embed(str(row.get("chunk_text", "")))
            dense_score = self.cosine(q_dense, list(dense_vec))

            # blend lexical relevance with dense fallback
            score = (0.75 * lexical_score) + (0.25 * dense_score)

            scored.append(
                {
                    "chunk_id": row.get("id"),
                    "source_id": row.get("source_id"),
                    "text": row.get("chunk_text"),
                    "title": row.get("title"),
                    "score": round(float(score), 4),
                    "lexical_score": round(float(lexical_score), 4),
                    "dense_score": round(float(dense_score), 4),
                    "author_type": row.get("author_type"),
                    "platform": row.get("platform"),
                    "content_type": row.get("content_type"),
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def _search_chroma(
        self,
        query: str,
        author_type: str | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        if self._collection is None:
            return []
        where: dict[str, Any] = {}
        if author_type:
            where["author_type"] = author_type
        if platform:
            where["platform"] = platform
        if content_type:
            where["content_type"] = content_type

        query_embedding = self.embed(query)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=max(limit, 1),
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        out: list[dict[str, object]] = []
        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            dist = float(dists[idx]) if idx < len(dists) else 1.0
            out.append(
                {
                    "chunk_id": meta.get("chunk_id"),
                    "source_id": meta.get("source_id"),
                    "text": doc,
                    "title": meta.get("title"),
                    "score": round(1.0 - dist, 4),
                    "lexical_score": 0.0,
                    "dense_score": round(1.0 - dist, 4),
                    "author_type": meta.get("author_type"),
                    "platform": meta.get("platform"),
                    "content_type": meta.get("content_type"),
                }
            )
        return out[:limit]

    def sync_source_chunks(self, source_id: int, chunks: list[dict[str, Any]]) -> None:
        if self._collection is None:
            return
        # Replace all vectors for this source to keep index consistent with db chunks.
        self.delete_source(source_id)
        ids: list[str] = []
        docs: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        for chunk in chunks:
            chunk_index = int(chunk.get("chunk_index", 0))
            text = str(chunk.get("chunk_text", ""))
            ids.append(f"{source_id}:{chunk_index}")
            docs.append(text)
            embeddings.append(self.embed(text))
            metadatas.append(
                {
                    "chunk_id": chunk.get("id"),
                    "source_id": source_id,
                    "title": chunk.get("title"),
                    "author_type": chunk.get("author_type"),
                    "platform": chunk.get("platform"),
                    "content_type": chunk.get("content_type"),
                    "chunk_index": chunk_index,
                }
            )
        if ids:
            self._collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)

    def delete_source(self, source_id: int) -> None:
        if self._collection is None:
            return
        self._collection.delete(where={"source_id": int(source_id)})
