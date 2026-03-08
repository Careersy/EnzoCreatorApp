"""Graph database interface with Neo4j and in-memory fallback."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from content_ai_system.config import SETTINGS
from content_ai_system.models.types import StylePattern

try:
    from neo4j import GraphDatabase  # type: ignore
except ImportError:  # pragma: no cover
    GraphDatabase = None


class GraphClient:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None) -> None:
        self.uri = uri or SETTINGS.neo4j_uri
        self.user = user or SETTINGS.neo4j_user
        self.password = password or SETTINGS.neo4j_password
        self.driver = None
        self._seed = {
            "hooks": ["Contrarian opener", "Curiosity gap", "Data-backed hook"],
            "sentence_patterns": ["Short-short-long cadence", "One-line punchline every 4 lines"],
            "tone_rules": ["Confident", "Conversational", "Evidence-led"],
            "frameworks": ["Hook -> Insight -> Lesson -> Action"],
            "persuasion_techniques": ["Social proof", "Loss aversion", "Specificity"],
            "creators": ["Creator A", "Creator B"],
        }

        if GraphDatabase is not None:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        if self.driver is not None:
            self.driver.close()

    def run_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self.driver is None:
            return []
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def retrieve_style_patterns(
        self,
        topic: str,
        platform: str,
        creators: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve hooks, sentence patterns, tone, frameworks, and persuasion techniques."""
        query = """
MATCH (c:Creator)-[:USES]->(node)
OPTIONAL MATCH (topic:Topic)-[:CONNECTED_TO]->(c)
WHERE toLower(topic.name) = toLower($topic)
   OR toLower($topic) IN [k IN coalesce(c.keywords, []) | toLower(k)]
WITH c, node
WHERE $creators IS NULL OR c.name IN $creators
RETURN
  collect(DISTINCT CASE WHEN node:HookPattern THEN node.name END) AS hooks,
  collect(DISTINCT CASE WHEN node:SentenceStructure THEN node.name END) AS sentence_patterns,
  collect(DISTINCT CASE WHEN node:Tone THEN node.name END) AS tone_rules,
  collect(DISTINCT CASE WHEN node:ContentFramework THEN node.name END) AS frameworks,
  collect(DISTINCT CASE WHEN node:PersuasionTechnique THEN node.name END) AS persuasion_techniques,
  collect(DISTINCT c.name) AS creators
"""
        rows = self.run_query(
            query,
            {
                "topic": topic,
                "platform": platform,
                "creators": creators,
            },
        )
        if rows:
            row = rows[0]
            return {
                "raw_rows": rows,
                "style_pattern": StylePattern(
                    hooks=[x for x in row.get("hooks", []) if x],
                    sentence_patterns=[x for x in row.get("sentence_patterns", []) if x],
                    tone_rules=[x for x in row.get("tone_rules", []) if x],
                    frameworks=[x for x in row.get("frameworks", []) if x],
                    persuasion_techniques=[x for x in row.get("persuasion_techniques", []) if x],
                ),
                "creators": [x for x in row.get("creators", []) if x],
            }

        return {
            "raw_rows": [],
            "style_pattern": StylePattern(
                hooks=self._seed["hooks"],
                sentence_patterns=self._seed["sentence_patterns"],
                tone_rules=self._seed["tone_rules"],
                frameworks=self._seed["frameworks"],
                persuasion_techniques=self._seed["persuasion_techniques"],
            ),
            "creators": self._seed["creators"],
        }

    def retrieve_creator_mix(self, creator_weights: dict[str, float], topic: str, platform: str) -> dict[str, Any]:
        """Return style data for multiple creators so mixer can blend by weight."""
        blended: dict[str, list[str]] = {
            "hooks": [],
            "sentence_patterns": [],
            "tone_rules": [],
            "frameworks": [],
            "persuasion_techniques": [],
        }
        source_creators = []
        for creator in creator_weights:
            result = self.retrieve_style_patterns(topic=topic, platform=platform, creators=[creator])
            style: StylePattern = result["style_pattern"]
            source_creators.extend(result.get("creators", [creator]))
            for key, value in asdict(style).items():
                blended[key].extend(value)

        if not source_creators:
            fallback = self.retrieve_style_patterns(topic=topic, platform=platform)
            return fallback

        return {
            "raw_rows": [],
            "style_pattern": StylePattern(**{k: list(dict.fromkeys(v)) for k, v in blended.items()}),
            "creators": list(dict.fromkeys(source_creators)),
        }

    def record_engagement(self, hook_name: str, views: int, likes: int, comments: int, shares: int) -> None:
        query = """
MERGE (h:HookPattern {name: $hook_name})
MERGE (e:EngagementSignal {hook_name: $hook_name})
SET e.views = coalesce(e.views, 0) + $views,
    e.likes = coalesce(e.likes, 0) + $likes,
    e.comments = coalesce(e.comments, 0) + $comments,
    e.shares = coalesce(e.shares, 0) + $shares,
    e.updated_at = datetime()
MERGE (h)-[:DRIVES]->(e)
"""
        if self.driver is not None:
            self.run_query(
                query,
                {
                    "hook_name": hook_name,
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                },
            )
