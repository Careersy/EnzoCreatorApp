"""Extract user voice profile features from writing samples."""

from __future__ import annotations

import math
import re
from collections import Counter


class UserVoiceProfiler:
    @staticmethod
    def _sentences(text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _paragraphs(text: str) -> list[str]:
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    @staticmethod
    def _quantiles(values: list[int]) -> dict[str, float]:
        if not values:
            return {"p25": 0.0, "p50": 0.0, "p75": 0.0}
        ordered = sorted(values)
        n = len(ordered)

        def q(p: float) -> float:
            idx = int(round((n - 1) * p))
            return float(ordered[idx])

        return {"p25": q(0.25), "p50": q(0.50), "p75": q(0.75)}

    def extract_profile(self, texts: list[str]) -> dict[str, object]:
        corpus = "\n\n".join([t.strip() for t in texts if t.strip()])
        if not corpus:
            return {
                "sample_count": 0,
                "avg_sentence_words": 0,
                "sentence_std": 0,
                "avg_paragraph_sentences": 0,
                "rhetorical_question_rate": 0,
                "direct_address_rate": 0,
                "punctuation": {},
                "top_phrases": [],
                "preferred_verbs": [],
                "tone_markers": [],
                "sentence_length_quantiles": {"p25": 0.0, "p50": 0.0, "p75": 0.0},
                "paragraph_length_quantiles": {"p25": 0.0, "p50": 0.0, "p75": 0.0},
                "cta_markers": [],
                "transition_markers": [],
                "story_assertion_ratio": 0.0,
                "formality_score": 0.0,
                "ai_phrase_risk_terms": [],
            }

        sentences = self._sentences(corpus)
        paragraphs = self._paragraphs(corpus)

        sentence_lengths = [len(s.split()) for s in sentences] or [0]
        avg_sentence_words = sum(sentence_lengths) / max(1, len(sentence_lengths))
        variance = sum((n - avg_sentence_words) ** 2 for n in sentence_lengths) / max(1, len(sentence_lengths))
        sentence_std = math.sqrt(variance)

        para_sentence_counts = [len(self._sentences(p)) for p in paragraphs] or [0]
        avg_paragraph_sentences = sum(para_sentence_counts) / max(1, len(para_sentence_counts))
        paragraph_word_lengths = [len(p.split()) for p in paragraphs] or [0]

        q_count = sum(1 for s in sentences if s.endswith("?"))
        rhetorical_question_rate = q_count / max(1, len(sentences))

        words = [w.strip(".,!?;:\"'()[]").lower() for w in corpus.split()]
        words = [w for w in words if w]
        direct_address_rate = words.count("you") / max(1, len(words))

        punctuation = {
            "exclamation_rate": corpus.count("!") / max(1, len(sentences)),
            "question_rate": corpus.count("?") / max(1, len(sentences)),
            "dash_rate": corpus.count("-") / max(1, len(sentences)),
            "colon_rate": corpus.count(":") / max(1, len(sentences)),
        }

        phrase_counter = Counter()
        for i in range(len(words) - 1):
            a, b = words[i], words[i + 1]
            if len(a) > 2 and len(b) > 2:
                phrase_counter[f"{a} {b}"] += 1

        verbs = [w for w in words if w.endswith("ing") or w.endswith("ed")]
        verb_counts = Counter(verbs)

        tone_keywords = ["honestly", "frankly", "directly", "clearly", "maybe", "probably", "definitely"]
        tone_markers = [k for k in tone_keywords if k in words]

        transition_terms = ["however", "but", "so", "therefore", "meanwhile", "still", "yet", "because"]
        transition_markers = [t for t in transition_terms if t in words]

        cta_terms = ["comment", "reply", "dm", "message", "subscribe", "follow", "book", "download", "click"]
        cta_hits = [t for t in cta_terms if t in words]

        story_terms = {"i", "my", "me", "we", "our"}
        assertion_terms = {"should", "must", "need", "will", "always", "never"}
        story_count = sum(1 for w in words if w in story_terms)
        assertion_count = sum(1 for w in words if w in assertion_terms)
        story_assertion_ratio = story_count / max(1, assertion_count)

        formal_terms = {"therefore", "moreover", "furthermore", "consequently", "hence"}
        informal_terms = {"kinda", "sorta", "gonna", "wanna", "yeah"}
        formality_score = (sum(1 for w in words if w in formal_terms) - sum(1 for w in words if w in informal_terms)) / max(
            1, len(words)
        )

        ai_risk_terms = [
            "leverage",
            "robust",
            "seamless",
            "unlock",
            "in conclusion",
            "ever-evolving",
            "game changer",
        ]
        ai_hits = [term for term in ai_risk_terms if term in corpus.lower()]

        return {
            "sample_count": len(texts),
            "avg_sentence_words": round(avg_sentence_words, 2),
            "sentence_std": round(sentence_std, 2),
            "avg_paragraph_sentences": round(avg_paragraph_sentences, 2),
            "rhetorical_question_rate": round(rhetorical_question_rate, 3),
            "direct_address_rate": round(direct_address_rate, 4),
            "punctuation": punctuation,
            "top_phrases": [p for p, _ in phrase_counter.most_common(20)],
            "preferred_verbs": [v for v, _ in verb_counts.most_common(20)],
            "tone_markers": tone_markers,
            "sentence_length_quantiles": self._quantiles(sentence_lengths),
            "paragraph_length_quantiles": self._quantiles(paragraph_word_lengths),
            "cta_markers": cta_hits,
            "transition_markers": transition_markers,
            "story_assertion_ratio": round(story_assertion_ratio, 3),
            "formality_score": round(formality_score, 5),
            "ai_phrase_risk_terms": ai_hits,
        }
