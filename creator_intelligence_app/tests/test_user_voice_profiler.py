from __future__ import annotations

import unittest

from creator_intelligence_app.style.user_voice_profiler import UserVoiceProfiler


class UserVoiceProfilerTest(unittest.TestCase):
    def test_extract_profile_basic_metrics(self) -> None:
        profiler = UserVoiceProfiler()
        texts = [
            "You should test this today. It works because it's specific. Do you see why?",
            "I write short paragraphs. You can skim this quickly.",
        ]
        profile = profiler.extract_profile(texts)

        self.assertGreater(profile["sample_count"], 0)
        self.assertGreater(profile["avg_sentence_words"], 0)
        self.assertIn("top_phrases", profile)


if __name__ == "__main__":
    unittest.main()
