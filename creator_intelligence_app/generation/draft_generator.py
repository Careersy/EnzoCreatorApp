"""Draft generation engine with retrieval-first style blending."""

from __future__ import annotations

from typing import Any

from creator_intelligence_app.app.services.llm_client import LLMClient, build_generation_prompt
from creator_intelligence_app.style.anti_ai_detector import AntiAIDetector
from creator_intelligence_app.style.scoring import StyleScorer


class DraftGenerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.detector = AntiAIDetector()
        self.scorer = StyleScorer()

    def generate(
        self,
        topic: str,
        platform: str,
        audience: str,
        goal: str,
        cta_goal: str,
        reference_content: str,
        blueprint: dict[str, Any],
        user_profile: dict[str, Any],
        banned_phrases: list[str],
        preferred_phrases: list[str],
        model: str | None = None,
    ) -> dict[str, Any]:
        input_text = f"Topic: {topic}\nCTA goal: {cta_goal}\nReference: {reference_content or 'none'}"
        system, prompt = build_generation_prompt(
            mode="generate",
            platform=platform,
            goal=goal,
            input_text=input_text,
            blueprint=blueprint,
            audience=audience,
        )
        draft = self.llm_client.complete(system, prompt, model=model)

        risk = self.detector.evaluate(draft, banned_phrases=banned_phrases)
        style_match = self.scorer.score_style_match(draft, user_profile)
        creator_align = self.scorer.score_creator_alignment(blueprint, draft)
        platform_fit = self.scorer.score_platform_fit(platform, draft)

        hooks = [
            f"{topic}: the uncomfortable truth most people miss",
            f"If you want better {topic} outcomes, start here",
            f"The {topic} playbook that actually compounds",
        ]
        ctas = [
            "Reply with your biggest bottleneck and I will suggest one fix.",
            "Comment 'framework' and I will share the structure.",
        ]

        revised = draft
        if risk.get("genericity_risk", 0) > 45:
            revised = self.detector.reduce_genericity(
                draft,
                banned_phrases=banned_phrases,
                preferred_phrases=preferred_phrases,
            )
            revised += "\n\n[Revision note: tightened language to reduce generic phrasing.]"

        return {
            "final_draft": revised,
            "alternate_hooks": hooks,
            "cta_options": ctas,
            "model_used": model,
            "style_notes": [
                "User voice weighting set as primary",
                "Creator patterns used as structural scaffolding",
            ],
            "scores": {
                "user_style_match": style_match,
                "creator_alignment": creator_align,
                "platform_fit": platform_fit,
                "ai_genericity_risk": risk.get("genericity_risk", 0),
            },
            "ai_genericity_notes": risk,
        }
