"""Rewrite existing content using graph-derived style patterns."""

from __future__ import annotations

from content_ai_system.generation.llm_client import LLMClient
from content_ai_system.models.types import RewriteRequest
from content_ai_system.prompts.templates import rewrite_prompt
from content_ai_system.retrieval.blueprint_builder import StyleBlueprintBuilder
from content_ai_system.retrieval.graph_retriever import GraphStyleRetriever


class ContentRewriteEngine:
    def __init__(
        self,
        retriever: GraphStyleRetriever,
        blueprint_builder: StyleBlueprintBuilder,
        llm_client: LLMClient,
    ) -> None:
        self.retriever = retriever
        self.blueprint_builder = blueprint_builder
        self.llm_client = llm_client

    def rewrite(self, req: RewriteRequest) -> str:
        retrieval = self.retriever.retrieve(
            user_query=f"Rewrite for {req.platform} with strong hook and structure",
        )
        blueprint = self.blueprint_builder.build(retrieval)
        system, user = rewrite_prompt(req=req, blueprint=blueprint)
        return self.llm_client.generate(system_prompt=system, user_prompt=user)
