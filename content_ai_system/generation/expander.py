"""Expand short-form content into long-form outputs."""

from __future__ import annotations

from content_ai_system.generation.llm_client import LLMClient
from content_ai_system.models.types import ExpansionRequest
from content_ai_system.prompts.templates import expansion_prompt
from content_ai_system.retrieval.blueprint_builder import StyleBlueprintBuilder
from content_ai_system.retrieval.graph_retriever import GraphStyleRetriever


class ContentExpander:
    def __init__(
        self,
        retriever: GraphStyleRetriever,
        blueprint_builder: StyleBlueprintBuilder,
        llm_client: LLMClient,
    ) -> None:
        self.retriever = retriever
        self.blueprint_builder = blueprint_builder
        self.llm_client = llm_client

    def expand(self, req: ExpansionRequest) -> str:
        retrieval = self.retriever.retrieve(
            user_query=f"Expand to {req.target_format} for {req.audience}",
        )
        blueprint = self.blueprint_builder.build(retrieval)
        system, user = expansion_prompt(req=req, blueprint=blueprint)
        return self.llm_client.generate(system_prompt=system, user_prompt=user)
