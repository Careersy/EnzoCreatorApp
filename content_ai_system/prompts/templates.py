"""Prompt templates for generation workflows."""

from __future__ import annotations

from content_ai_system.models.types import ExpansionRequest, GenerationRequest, RewriteRequest, StyleBlueprint


def generation_prompt(req: GenerationRequest, blueprint: StyleBlueprint) -> tuple[str, str]:
    system = (
        "You are an expert content strategist. Always apply the provided style blueprint. "
        "Return clean final output only."
    )
    user = (
        f"Platform: {req.platform}\n"
        f"Content type: {req.content_type}\n"
        f"Topic: {req.topic}\n"
        f"Audience: {req.audience}\n"
        f"Goal: {req.goal}\n"
        f"Extra context: {req.extra_context or 'none'}\n\n"
        "Style blueprint:\n"
        f"{blueprint.to_prompt_block()}\n\n"
        "Write the content now."
    )
    return system, user


def rewrite_prompt(req: RewriteRequest, blueprint: StyleBlueprint) -> tuple[str, str]:
    system = (
        "You rewrite content with stronger hooks and clearer structure while preserving the core idea. "
        "Return only rewritten content."
    )
    user = (
        f"Platform: {req.platform}\n"
        f"Goal: {req.goal}\n"
        f"Preserve core idea: {req.preserve_core_idea}\n\n"
        "Style blueprint:\n"
        f"{blueprint.to_prompt_block()}\n\n"
        "Original content:\n"
        f"{req.content}\n\n"
        "Rewrite now."
    )
    return system, user


def expansion_prompt(req: ExpansionRequest, blueprint: StyleBlueprint) -> tuple[str, str]:
    system = (
        "You expand short-form content into structured long-form writing with examples, arguments, "
        "and practical takeaways."
    )
    user = (
        f"Target format: {req.target_format}\n"
        f"Audience: {req.audience}\n\n"
        "Style blueprint:\n"
        f"{blueprint.to_prompt_block()}\n\n"
        "Source content:\n"
        f"{req.content}\n\n"
        "Expand this into long-form content with sections, examples, and a conclusion."
    )
    return system, user
