"""Graph retrieval wrapper for creator patterns."""

from __future__ import annotations

from creator_intelligence_app.graph.graph_client import GraphClient


class GraphRetriever:
    def __init__(self, graph_client: GraphClient) -> None:
        self.graph_client = graph_client

    def retrieve_patterns(self, query: str, platform: str | None = None) -> dict[str, object]:
        results = self.graph_client.query_natural_language(query)
        if platform:
            filtered = [
                item
                for item in results.get("records", [])
                if platform.lower() in str(item).lower() or not item.get("edge")
            ]
            results["records"] = filtered if filtered else results.get("records", [])
        return results
