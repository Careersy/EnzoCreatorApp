"""Ingest performance metrics and update graph relationships."""

from __future__ import annotations

from content_ai_system.knowledge_graph.graph_client import GraphClient


class PerformanceLearningLayer:
    def __init__(self, graph_client: GraphClient) -> None:
        self.graph_client = graph_client

    def ingest_post_metrics(
        self,
        hook_name: str,
        views: int,
        likes: int,
        comments: int,
        shares: int,
    ) -> None:
        self.graph_client.record_engagement(
            hook_name=hook_name,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
        )
