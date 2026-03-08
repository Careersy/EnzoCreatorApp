from __future__ import annotations

import unittest

from creator_intelligence_app.style.anti_ai_detector import AntiAIDetector


class AntiAIDetectorTest(unittest.TestCase):
    def test_detects_generic_and_banned_phrases(self) -> None:
        detector = AntiAIDetector()
        text = "In today's fast-paced world, it is important to note this is a game changer."
        result = detector.evaluate(text, banned_phrases=["game changer"])

        self.assertGreater(result["genericity_risk"], 0)
        self.assertIn("game changer", result["banned_hits"])

    def test_reduce_genericity(self) -> None:
        detector = AntiAIDetector()
        text = "In conclusion, leverage robust strategy. This is a game changer."
        cleaned = detector.reduce_genericity(text, banned_phrases=["game changer"], preferred_phrases=["direct point"])
        self.assertNotIn("game changer", cleaned.lower())
        self.assertNotIn("in conclusion", cleaned.lower())


if __name__ == "__main__":
    unittest.main()
