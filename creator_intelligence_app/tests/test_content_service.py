from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_intelligence_app.app.db.database import Database, init_db
from creator_intelligence_app.app.services.content_service import ContentIntelligenceService
from creator_intelligence_app.graph.graph_client import GraphClient
from creator_intelligence_app.integrations.github_export import GitHubExportService
from creator_intelligence_app.integrations.notion_sync import NotionSyncService


class ContentServiceIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        db_path = Path(self.tmp.name) / "test.db"
        init_db(db_path)
        db = Database(db_path)

        graph_path = Path.cwd() / "knowledge-graph.json"
        graph_client = GraphClient(db=db, graph_json_path=graph_path)

        self.service = ContentIntelligenceService(
            db=db,
            graph_client=graph_client,
            notion_service=NotionSyncService(enabled=False),
            github_service=GitHubExportService(enabled=False),
        )
        self.service.load_creator_graph()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_ingest_extract_and_generate(self) -> None:
        self.service.ingest_text(
            title="My sample",
            text="You should focus on specifics. I use short lines. Ask one sharp question?",
            author_type="mine",
            status="published",
            source_type="pasted_text",
            platform="LinkedIn",
            content_type="post",
            tags=["sample"],
        )
        self.service.ingest_text(
            title="Creator sample",
            text="The market changed. Here are 3 patterns I see.",
            author_type="creator",
            status="published",
            source_type="pasted_text",
            platform="LinkedIn",
            content_type="post",
            tags=["creator"],
        )

        profile = self.service.extract_style_profile()
        self.assertIn("metrics", profile)

        result = self.service.generate_content(
            topic="AI consulting",
            platform="LinkedIn",
            audience="founders",
            goal="authority",
            cta_goal="engagement",
            reference_content="",
        )
        self.assertIn("final_draft", result)
        self.assertIn("scores", result)

    def test_rewrite_returns_hooks_and_score(self) -> None:
        self.service.ingest_text(
            title="Mine 2",
            text="I prefer direct language. You can test this now.",
            author_type="mine",
            status="published",
            source_type="pasted_text",
            platform="LinkedIn",
            content_type="post",
        )
        self.service.extract_style_profile()

        out = self.service.rewrite_content(
            content="AI is important for business growth.",
            platform="LinkedIn",
            goal="authority",
            audience="founders",
        )
        self.assertTrue(out["stronger_hooks"])
        self.assertIn("style_similarity_score", out)
        self.assertIn("original_input", out)

    def test_dedupe_and_reindex(self) -> None:
        text = "This is a source. It has stable content for hashing."
        first = self.service.ingest_text(
            title="Hash sample",
            text=text,
            author_type="mine",
            status="published",
            source_type="pasted_text",
            platform="LinkedIn",
            content_type="post",
        )
        second = self.service.ingest_text(
            title="Hash sample duplicate",
            text=text,
            author_type="mine",
            status="published",
            source_type="pasted_text",
            platform="LinkedIn",
            content_type="post",
        )
        self.assertFalse(first.get("duplicated", False))
        self.assertTrue(second.get("duplicated", False))
        self.assertEqual(first["source_id"], second["source_id"])

        reindex = self.service.reindex_sources(source_id=first["source_id"])
        self.assertEqual(reindex["reindexed_sources"], 1)

    def test_job_lifecycle(self) -> None:
        job_id = self.service.create_job("ingest_file", {"file": "a.pdf"})
        job = self.service.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "queued")

    def test_planning_calendar_and_repurpose(self) -> None:
        self.service.ingest_text(
            title="My style seed",
            text="I write with short lines. I avoid fluff. I end with clear actions.",
            author_type="mine",
            status="published",
            source_type="pasted_text",
            platform="LinkedIn",
            content_type="post",
        )
        self.service.extract_style_profile()

        plan = self.service.plan_content_series(
            topic="AI consulting",
            platform="LinkedIn",
            audience="founders",
            goal="authority",
            weeks=2,
            posts_per_week=2,
        )
        self.assertIn("content_calendar", plan)
        self.assertGreaterEqual(len(plan["content_calendar"]), 4)

        calendar = self.service.plan_content_calendar(
            topic="AI consulting",
            platform="LinkedIn",
            audience="founders",
            goal="authority",
            weeks=2,
            posts_per_week=2,
        )
        self.assertEqual(calendar["weeks"], 2)
        self.assertEqual(calendar["posts_per_week"], 2)

        repurpose = self.service.repurpose_content(
            content="AI consulting is becoming a trust game, not a tooling game.",
            topic="AI consulting",
            source_platform="LinkedIn",
            target_platforms=["Newsletter", "Blog"],
            audience="founders",
            goal="authority",
        )
        self.assertIn("pipeline", repurpose)
        self.assertEqual(len(repurpose["variants"]), 2)

    def test_style_mixer_returns_blended_output(self) -> None:
        self.service.ingest_text(
            title="My style seed",
            text="I write with short lines and direct cadence.",
            author_type="mine",
            status="published",
            source_type="pasted_text",
            platform="LinkedIn",
            content_type="post",
        )
        self.service.extract_style_profile()
        creators = self.service.list_creators(limit=2)
        if not creators:
            self.skipTest("No creators loaded from graph")

        weights = [{"creator": creators[0], "weight": 70.0}]
        if len(creators) > 1:
            weights.append({"creator": creators[1], "weight": 30.0})

        out = self.service.mix_creator_patterns_with_my_voice(
            topic="AI strategy",
            platform="LinkedIn",
            audience="founders",
            goal="authority",
            creator_weights=weights,
            mode="generate",
            content="",
        )
        self.assertIn("creator_mix", out)
        self.assertIn("final_text", out)
        self.assertIn("blueprint", out)

    def test_performance_learning_updates_stats(self) -> None:
        event = self.service.ingest_performance_metrics(
            platform="LinkedIn",
            hook_text="Most founders miss this AI execution trap.",
            views=1200,
            likes=44,
            comments=8,
            shares=6,
            topic="AI consulting",
        )
        self.assertIn("event_id", event)
        self.assertGreater(event["engagement_score"], 0)

        summary = self.service.performance_summary(platform="LinkedIn", limit=5)
        self.assertIn("top_hooks", summary)
        self.assertTrue(summary["top_hooks"])


if __name__ == "__main__":
    unittest.main()
