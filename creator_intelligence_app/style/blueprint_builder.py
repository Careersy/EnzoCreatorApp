"""Build blended style blueprints with user voice as primary signal."""

from __future__ import annotations

from typing import Any


class BlueprintBuilder:
    def build(
        self,
        retrieval_bundle: dict[str, Any],
        user_profile: dict[str, Any] | None,
        creator_profile: dict[str, Any] | None,
        style_weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        graph_patterns = retrieval_bundle.get("graph_patterns", {})
        style_matches = retrieval_bundle.get("style_matches", [])

        hooks = [
            item.get("pattern")
            for item in graph_patterns.get("records", [])
            if item.get("pattern")
        ][:8]
        if not hooks:
            hooks = [h for h in graph_patterns.get("strongest_hooks", []) if h][:6]

        use_section = {
            "voice": [
                "Use user cadence and punctuation habits first",
                "Preserve directness and specific phrasing from user samples",
            ],
            "hooks": hooks[:5],
            "frameworks": [
                "Hook -> Insight -> Lesson -> Action",
                "Problem -> Diagnosis -> Shift -> CTA",
            ],
            "cta_options": [
                "Invite a specific response in comments",
                "Offer one concrete next step",
            ],
        }

        prefer_section = {
            "sentence_rhythm": {
                "avg_sentence_words": (user_profile or {}).get("avg_sentence_words", 14),
                "sentence_std": (user_profile or {}).get("sentence_std", 6),
                "quantiles": (user_profile or {}).get("sentence_length_quantiles", {}),
            },
            "paragraph_pacing": {
                "avg_paragraph_sentences": (user_profile or {}).get("avg_paragraph_sentences", 2),
                "quantiles": (user_profile or {}).get("paragraph_length_quantiles", {}),
            },
            "preferred_phrases": retrieval_bundle.get("preferred_phrases", [])[:10],
            "style_examples": [m.get("text", "")[:220] for m in style_matches[:3]],
            "cta_markers": (user_profile or {}).get("cta_markers", []),
            "transition_markers": (user_profile or {}).get("transition_markers", []),
            "performance_validated_hooks": [
                f"{row.get('hook_text')} (avg score {row.get('avg_engagement_score')})"
                for row in retrieval_bundle.get("performance_hooks", [])[:5]
            ],
        }

        avoid_section = {
            "banned_phrases": retrieval_bundle.get("banned_phrases", []),
            "generic_ai_patterns": [
                "Over-polished transitions",
                "Vague abstractions",
                "Synthetic enthusiasm",
                "Over-explaining",
            ],
        }

        unclear_section = {
            "insufficient_evidence": [],
        }
        if not user_profile or user_profile.get("sample_count", 0) < 3:
            unclear_section["insufficient_evidence"].append(
                "User style profile is based on limited samples. Upload more personal writing."
            )

        return {
            "use": use_section,
            "prefer": prefer_section,
            "avoid": avoid_section,
            "unclear": unclear_section,
            "weights": {
                "user_voice": (style_weights or {}).get("user_voice", 0.65),
                "creator_patterns": (style_weights or {}).get("creator_patterns", 0.25),
                "platform_rules": (style_weights or {}).get("platform_rules", 0.10),
            },
            "creator_profile": creator_profile or {},
            "confidence": "medium" if unclear_section["insufficient_evidence"] else "high",
        }
