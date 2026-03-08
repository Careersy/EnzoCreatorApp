"""Content generator that always retrieves style patterns from graph first."""

from __future__ import annotations

from content_ai_system.generation.llm_client import LLMClient
from content_ai_system.models.types import GenerationRequest, StyleBlueprint
from content_ai_system.prompts.templates import generation_prompt
from content_ai_system.retrieval.blueprint_builder import StyleBlueprintBuilder
from content_ai_system.retrieval.graph_retriever import GraphStyleRetriever


class ContentGenerator:
    def __init__(
        self,
        retriever: GraphStyleRetriever,
        blueprint_builder: StyleBlueprintBuilder,
        llm_client: LLMClient,
    ) -> None:
        self.retriever = retriever
        self.blueprint_builder = blueprint_builder
        self.llm_client = llm_client

    def retrieve_blueprint(self, req: GenerationRequest) -> StyleBlueprint:
        retrieval_result = self.retriever.retrieve(
            user_query=f"Generate a {req.platform} {req.content_type} about {req.topic} for {req.audience}",
        )
        return self.blueprint_builder.build(retrieval_result=retrieval_result)

    def generate(self, req: GenerationRequest) -> str:
        blueprint = self.retrieve_blueprint(req)
        system, user = generation_prompt(req=req, blueprint=blueprint)
        return self.llm_client.generate(system_prompt=system, user_prompt=user)
