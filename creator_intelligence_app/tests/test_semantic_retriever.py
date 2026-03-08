from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_intelligence_app.app.db.database import Database, init_db
from creator_intelligence_app.retrieval.semantic_retriever import SemanticRetriever


class SemanticRetrieverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        db_path = Path(self.tmp.name) / "test.db"
        init_db(db_path)
        self.db = Database(db_path)

        s1 = self.db.add_source(
            {
                "title": "A",
                "source_type": "pasted_text",
                "source_hash": "h1",
                "author_type": "mine",
                "platform": "LinkedIn",
                "content_type": "post",
                "raw_text": "AI consulting for founders requires clear positioning.",
                "metadata": {},
            }
        )
        s2 = self.db.add_source(
            {
                "title": "B",
                "source_type": "pasted_text",
                "source_hash": "h2",
                "author_type": "mine",
                "platform": "LinkedIn",
                "content_type": "post",
                "raw_text": "Cooking recipes and kitchen prep tips.",
                "metadata": {},
            }
        )
        self.db.add_chunks(
            s1,
            [
                {
                    "chunk_index": 0,
                    "chunk_text": "AI consulting for founders requires clear positioning.",
                    "platform": "LinkedIn",
                    "content_type": "post",
                    "author_type": "mine",
                }
            ],
        )
        self.db.add_chunks(
            s2,
            [
                {
                    "chunk_index": 0,
                    "chunk_text": "Cooking recipes and kitchen prep tips.",
                    "platform": "LinkedIn",
                    "content_type": "post",
                    "author_type": "mine",
                }
            ],
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_relevant_chunk_ranks_higher(self) -> None:
        retriever = SemanticRetriever(self.db)
        rows = retriever.search("AI consulting positioning", author_type="mine", limit=2)
        self.assertEqual(len(rows), 2)
        self.assertIn("AI consulting", rows[0]["text"])


if __name__ == "__main__":
    unittest.main()
