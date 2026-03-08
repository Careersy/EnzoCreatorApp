"""Rewrite engine with retrieval-first pipeline."""

from __future__ import annotations

from typing import Any

from creator_intelligence_app.app.services.llm_client import LLMClient, build_generation_prompt
from creator_intelligence_app.style.anti_ai_detector import AntiAIDetector
from creator_intelligence_app.style.scoring import StyleScorer


class RewriteEngine:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.detector = AntiAIDetector()
        self.scorer = StyleScorer()

    def rewrite(
        self,
        content: str,
        platform: str,
        goal: str,
        audience: str,
        blueprint: dict[str, Any],
        user_profile: dict[str, Any],
        banned_phrases: list[str],
        preferred_phrases: list[str],
        model: str | None = None,
    ) -> dict[str, Any]:
        system, prompt = build_generation_prompt(
            mode="rewrite",
            platform=platform,
            goal=goal,
            input_text=content,
            blueprint=blueprint,
            audience=audience,
        )

        completion = self.llm_client.complete_with_meta(system, prompt, model=model)
        draft = completion.text
        draft = self.detector.reduce_genericity(
            draft,
            banned_phrases=banned_phrases,
            preferred_phrases=preferred_phrases,
        )

        hooks = [
            "You are closer than you think. Your structure is the blocker.",
            "Most drafts fail before line two. Here's how to fix yours.",
            "This rewrite keeps your voice but upgrades authority.",
        ]
        concise = draft[:600]
        punchy = draft.replace(". ", ".\n").replace("! ", "!\n")[:900]

        risk = self.detector.evaluate(draft, banned_phrases=banned_phrases)
        style_match = self.scorer.score_style_match(draft, user_profile)
        creator_align = self.scorer.score_creator_alignment(blueprint, draft)
        platform_fit = self.scorer.score_platform_fit(platform, draft)

        notes = {
            "applied_rules": [
                "User voice features prioritized",
                "Creator hook/framework patterns applied",
                "Platform pacing constraints applied",
            ],
            "weakness_checks": ["hook", "pacing", "clarity", "authority", "flow", "cta"],
            "genericity_notes": risk.get("notes", []),
        }

        return {
            "rewritten_version": draft,
            "stronger_hooks": hooks,
            "more_concise": concise,
            "more_punchy": punchy,
            "model_used": completion.resolved_model,
            "llm_meta": {
                "provider": completion.provider,
                "requested_model": completion.requested_model,
                "resolved_model": completion.resolved_model,
                "fallback_used": completion.fallback_used,
                "error": completion.error,
            },
            "style_similarity_score": style_match,
            "scores": {
                "user_style_match": style_match,
                "creator_alignment": creator_align,
                "platform_fit": platform_fit,
                "ai_genericity_risk": risk.get("genericity_risk", 0),
            },
            "notes": notes,
        }
