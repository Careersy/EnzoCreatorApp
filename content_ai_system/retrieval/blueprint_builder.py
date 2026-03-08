"""Builds style blueprints from retrieval results."""

from __future__ import annotations

from content_ai_system.models.types import RetrievalResult, StyleBlueprint


class StyleBlueprintBuilder:
    def build(self, retrieval_result: RetrievalResult, source_creators: list[str] | None = None) -> StyleBlueprint:
        style = retrieval_result.style_pattern
        sentence_rules = list(dict.fromkeys(style.sentence_patterns))
        if retrieval_result.related_examples:
            sentence_rules.append("Reference top semantic examples for cadence and specificity")

        return StyleBlueprint(
            voice=list(dict.fromkeys(style.tone_rules)),
            sentence_rules=sentence_rules,
            hooks=list(dict.fromkeys(style.hooks)),
            framework=list(dict.fromkeys(style.frameworks)),
            persuasion=list(dict.fromkeys(style.persuasion_techniques)),
            source_creators=source_creators or [],
        )
