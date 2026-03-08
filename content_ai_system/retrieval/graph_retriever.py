"""GraphRAG retrieval orchestration."""

from __future__ import annotations

from dataclasses import asdict

from content_ai_system.knowledge_graph.graph_client import GraphClient
from content_ai_system.models.types import RetrievalResult, StylePattern
from content_ai_system.retrieval.vector_retriever import LocalVectorRetriever


class GraphStyleRetriever:
    def __init__(self, graph_client: GraphClient, vector_retriever: LocalVectorRetriever | None = None) -> None:
        self.graph_client = graph_client
        self.vector_retriever = vector_retriever

    def query_to_graph_params(self, user_query: str) -> tuple[str, str]:
        lowered = user_query.lower()
        platform = "LinkedIn"
        if "substack" in lowered or "newsletter" in lowered:
            platform = "Substack"
        elif "blog" in lowered or "article" in lowered:
            platform = "Blog"

        topic = user_query
        markers = ["about", "on", "for"]
        for marker in markers:
            if f" {marker} " in lowered:
                topic = user_query[lowered.index(f" {marker} ") + len(marker) + 2 :].strip()
                break

        return topic.strip() or user_query, platform

    def retrieve(self, user_query: str) -> RetrievalResult:
        topic, platform = self.query_to_graph_params(user_query)
        raw = self.graph_client.retrieve_style_patterns(topic=topic, platform=platform)

        style_pattern: StylePattern = raw["style_pattern"]
        examples: list[str] = []
        if self.vector_retriever is not None:
            examples = self.vector_retriever.similarity_search(user_query, k=4)

        return RetrievalResult(
            raw_graph_rows=raw.get("raw_rows", []),
            style_pattern=style_pattern,
            related_examples=examples,
        )

    def retrieve_for_creator_mix(
        self,
        topic: str,
        platform: str,
        creator_weights: dict[str, float],
    ) -> RetrievalResult:
        raw = self.graph_client.retrieve_creator_mix(
            creator_weights=creator_weights,
            topic=topic,
            platform=platform,
        )
        style_pattern: StylePattern = raw["style_pattern"]
        return RetrievalResult(
            raw_graph_rows=raw.get("raw_rows", []),
            style_pattern=style_pattern,
            related_examples=[],
        )

    @staticmethod
    def flatten_style(style_pattern: StylePattern) -> dict[str, list[str]]:
        return {k: list(dict.fromkeys(v)) for k, v in asdict(style_pattern).items()}
