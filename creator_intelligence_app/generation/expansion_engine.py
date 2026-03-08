"""Expansion engine for short-to-long content transformations."""

from __future__ import annotations

from typing import Any

from creator_intelligence_app.app.services.llm_client import LLMClient, build_generation_prompt
from creator_intelligence_app.style.anti_ai_detector import AntiAIDetector
from creator_intelligence_app.style.scoring import StyleScorer


class ExpansionEngine:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.detector = AntiAIDetector()
        self.scorer = StyleScorer()

    def expand(
        self,
        content: str,
        target_format: str,
        audience: str,
        goal: str,
        blueprint: dict[str, Any],
        user_profile: dict[str, Any],
        banned_phrases: list[str],
        preferred_phrases: list[str],
        model: str | None = None,
    ) -> dict[str, Any]:
        system, prompt = build_generation_prompt(
            mode="expand",
            platform=target_format,
            goal=goal,
            input_text=content,
            blueprint=blueprint,
            audience=audience,
        )
        completion = self.llm_client.complete_with_meta(system, prompt, model=model)
        full_draft = completion.text
        full_draft = self.detector.reduce_genericity(
            full_draft,
            banned_phrases=banned_phrases,
            preferred_phrases=preferred_phrases,
        )

        titles = [
            f"A Practical {target_format} Guide: From Insight to Action",
            f"What Most People Miss About This Topic ({target_format} Edition)",
            f"How to Apply This Idea Without Sounding Generic",
        ]
        outline = [
            "Hook and context",
            "Core argument",
            "3 practical examples",
            "Counterpoint and nuance",
            "Actionable conclusion and CTA",
        ]

        risk = self.detector.evaluate(full_draft, banned_phrases=banned_phrases)
        style_match = self.scorer.score_style_match(full_draft, user_profile)
        platform_fit = self.scorer.score_platform_fit(target_format, full_draft)

        return {
            "title_options": titles,
            "outline": outline,
            "full_draft": full_draft,
            "model_used": completion.resolved_model,
            "llm_meta": {
                "provider": completion.provider,
                "requested_model": completion.requested_model,
                "resolved_model": completion.resolved_model,
                "fallback_used": completion.fallback_used,
                "error": completion.error,
            },
            "shorter_version": full_draft[:1200],
            "style_fidelity_notes": {
                "user_style_match": style_match,
                "platform_fit": platform_fit,
                "ai_genericity_risk": risk.get("genericity_risk", 0),
                "notes": risk.get("notes", []),
            },
        }
