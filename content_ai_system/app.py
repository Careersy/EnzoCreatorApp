"""Dependency wiring helpers for CLI and application usage."""

from __future__ import annotations

from content_ai_system.generation.content_generator import ContentGenerator
from content_ai_system.generation.expander import ContentExpander
from content_ai_system.generation.llm_client import LLMClient
from content_ai_system.generation.rewrite_engine import ContentRewriteEngine
from content_ai_system.generation.style_mixer import CreatorStyleMixer
from content_ai_system.knowledge_graph.graph_client import GraphClient
from content_ai_system.performance.performance_learner import PerformanceLearningLayer
from content_ai_system.planning.content_os import ContentOSEngine
from content_ai_system.retrieval.blueprint_builder import StyleBlueprintBuilder
from content_ai_system.retrieval.graph_retriever import GraphStyleRetriever
from content_ai_system.retrieval.vector_retriever import LocalVectorRetriever


def build_system() -> dict[str, object]:
    graph_client = GraphClient()
    vector_retriever = LocalVectorRetriever()
    style_retriever = GraphStyleRetriever(graph_client=graph_client, vector_retriever=vector_retriever)
    blueprint_builder = StyleBlueprintBuilder()
    llm_client = LLMClient()

    generator = ContentGenerator(
        retriever=style_retriever,
        blueprint_builder=blueprint_builder,
        llm_client=llm_client,
    )
    rewrite_engine = ContentRewriteEngine(
        retriever=style_retriever,
        blueprint_builder=blueprint_builder,
        llm_client=llm_client,
    )
    expander = ContentExpander(
        retriever=style_retriever,
        blueprint_builder=blueprint_builder,
        llm_client=llm_client,
    )
    style_mixer = CreatorStyleMixer(
        retriever=style_retriever,
        blueprint_builder=blueprint_builder,
        llm_client=llm_client,
    )
    content_os = ContentOSEngine(generator=generator)
    performance_layer = PerformanceLearningLayer(graph_client=graph_client)

    return {
        "graph_client": graph_client,
        "vector_retriever": vector_retriever,
        "retriever": style_retriever,
        "generator": generator,
        "rewrite_engine": rewrite_engine,
        "expander": expander,
        "style_mixer": style_mixer,
        "content_os": content_os,
        "performance_layer": performance_layer,
    }
