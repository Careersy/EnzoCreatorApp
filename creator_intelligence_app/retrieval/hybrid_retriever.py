"""Hybrid retriever: graph + semantic + metadata + style matching."""

from __future__ import annotations

from typing import Any

from creator_intelligence_app.retrieval.graph_retriever import GraphRetriever
from creator_intelligence_app.retrieval.semantic_retriever import SemanticRetriever
from creator_intelligence_app.retrieval.style_matcher import StyleMatcher


class HybridRetriever:
    def __init__(
        self,
        graph_retriever: GraphRetriever,
        semantic_retriever: SemanticRetriever,
        style_matcher: StyleMatcher,
    ) -> None:
        self.graph_retriever = graph_retriever
        self.semantic_retriever = semantic_retriever
        self.style_matcher = style_matcher

    def retrieve(
        self,
        query: str,
        platform: str,
        goal: str,
        audience: str,
        content_type: str,
    ) -> dict[str, Any]:
        graph_hits = self.graph_retriever.retrieve_patterns(query=query, platform=platform)

        user_semantic = self.semantic_retriever.search(
            query=query,
            author_type="mine",
            platform=platform,
            content_type=content_type,
            limit=6,
        )
        creator_semantic = self.semantic_retriever.search(
            query=query,
            author_type="creator",
            platform=platform,
            content_type=content_type,
            limit=6,
        )

        style_examples = self.style_matcher.top_matching_user_examples(reference_text=query, limit=5)

        return {
            "query": query,
            "constraints": {
                "platform": platform,
                "goal": goal,
                "audience": audience,
                "content_type": content_type,
            },
            "graph_patterns": graph_hits,
            "semantic_user_examples": user_semantic,
            "semantic_creator_examples": creator_semantic,
            "style_matches": style_examples,
            "banned_phrases": self.style_matcher.banned_phrases(),
            "overused_phrases": self.style_matcher.overused_phrases(),
            "preferred_phrases": self.style_matcher.preferred_phrases(),
        }
