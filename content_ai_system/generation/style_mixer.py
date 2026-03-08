"""Blend multiple creator styles with explicit weighting."""

from __future__ import annotations

from content_ai_system.generation.llm_client import LLMClient
from content_ai_system.models.types import GenerationRequest
from content_ai_system.prompts.templates import generation_prompt
from content_ai_system.retrieval.blueprint_builder import StyleBlueprintBuilder
from content_ai_system.retrieval.graph_retriever import GraphStyleRetriever


class CreatorStyleMixer:
    def __init__(
        self,
        retriever: GraphStyleRetriever,
        blueprint_builder: StyleBlueprintBuilder,
        llm_client: LLMClient,
    ) -> None:
        self.retriever = retriever
        self.blueprint_builder = blueprint_builder
        self.llm_client = llm_client

    def generate_with_mix(
        self,
        req: GenerationRequest,
        creator_weights: dict[str, float],
    ) -> str:
        retrieval = self.retriever.retrieve_for_creator_mix(
            topic=req.topic,
            platform=req.platform,
            creator_weights=creator_weights,
        )
        sorted_creators = [
            creator
            for creator, _weight in sorted(creator_weights.items(), key=lambda x: x[1], reverse=True)
        ]
        blueprint = self.blueprint_builder.build(
            retrieval_result=retrieval,
            source_creators=sorted_creators,
        )

        system, user = generation_prompt(req=req, blueprint=blueprint)
        mix_line = "\n".join([f"- {k}: {v:.0%}" for k, v in creator_weights.items()])
        user = f"{user}\n\nApply creator mix:\n{mix_line}"

        return self.llm_client.generate(system_prompt=system, user_prompt=user)
