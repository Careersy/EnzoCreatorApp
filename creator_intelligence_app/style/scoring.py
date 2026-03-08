"""Scoring helpers for style fidelity and output quality."""

from __future__ import annotations

from typing import Any

from creator_intelligence_app.style.user_voice_profiler import UserVoiceProfiler


class StyleScorer:
    def __init__(self) -> None:
        self.profiler = UserVoiceProfiler()

    def score_style_match(self, text: str, user_profile: dict[str, Any]) -> float:
        live = self.profiler.extract_profile([text])
        if not user_profile:
            return 50.0

        deltas = []
        keys = [
            "avg_sentence_words",
            "sentence_std",
            "avg_paragraph_sentences",
            "rhetorical_question_rate",
            "direct_address_rate",
            "story_assertion_ratio",
            "formality_score",
        ]
        for key in keys:
            a = float(live.get(key, 0) or 0)
            b = float(user_profile.get(key, 0) or 0)
            deltas.append(abs(a - b))

        live_punc = live.get("punctuation", {}) if isinstance(live.get("punctuation"), dict) else {}
        user_punc = user_profile.get("punctuation", {}) if isinstance(user_profile.get("punctuation"), dict) else {}
        for key in ("question_rate", "dash_rate", "colon_rate"):
            deltas.append(abs(float(live_punc.get(key, 0.0)) - float(user_punc.get(key, 0.0))))

        distance = sum(deltas) / max(1, len(deltas))
        score = max(0.0, 100.0 - (distance * 11.0))
        return round(score, 1)

    @staticmethod
    def score_platform_fit(platform: str, text: str) -> float:
        word_count = len(text.split())
        platform_low = platform.lower()

        if platform_low == "linkedin":
            if 80 <= word_count <= 260:
                return 85.0
            if 50 <= word_count <= 320:
                return 70.0
            return 55.0

        if platform_low in {"newsletter", "substack"}:
            if 250 <= word_count <= 1200:
                return 85.0
            return 65.0

        if platform_low in {"blog", "article"}:
            if 600 <= word_count <= 2200:
                return 82.0
            return 62.0

        return 70.0

    @staticmethod
    def score_creator_alignment(blueprint: dict[str, Any], text: str) -> float:
        hooks = []
        for item in blueprint.get("use", {}).get("hooks", []):
            if isinstance(item, str):
                hooks.append(item.lower())
            elif isinstance(item, dict):
                hooks.append(str(item.get("name", "")).lower())
            else:
                hooks.append(str(item).lower())
        if not hooks:
            return 65.0

        lower = text.lower()
        hit_count = sum(1 for hook in hooks if hook and hook.split()[0] in lower)
        return round(min(100.0, 60.0 + hit_count * 10.0), 1)
