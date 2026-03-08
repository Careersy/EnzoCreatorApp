"""Database schema and query examples for the creator knowledge graph."""

from __future__ import annotations

NODE_TYPES = {
    "Creator": ["name", "niche", "platforms"],
    "HookPattern": ["name", "formula", "intent"],
    "SentenceStructure": ["name", "pattern", "rhythm"],
    "Tone": ["name", "descriptors"],
    "ContentFramework": ["name", "steps"],
    "PersuasionTechnique": ["name", "principle"],
    "Topic": ["name", "keywords"],
    "ContentType": ["name", "platform"],
}

RELATIONSHIP_TYPES = {
    "(:Creator)-[:USES]->(:HookPattern)": "Creator uses a hook style",
    "(:Creator)-[:USES]->(:ContentFramework)": "Creator uses a framework",
    "(:Creator)-[:USES]->(:Tone)": "Creator uses a tone",
    "(:Creator)-[:USES]->(:SentenceStructure)": "Creator uses a sentence pattern",
    "(:ContentFramework)-[:SUITABLE_FOR]->(:ContentType)": "Framework fit",
    "(:HookPattern)-[:INCREASES]->(:EngagementSignal)": "Measured engagement",
    "(:Topic)-[:CONNECTED_TO]->(:Creator)": "Topic-to-creator mapping",
    "(:PersuasionTechnique)-[:APPEARS_IN]->(:ContentFramework)": "Technique placement",
}

CONSTRAINT_QUERIES = [
    "CREATE CONSTRAINT creator_name IF NOT EXISTS FOR (c:Creator) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT hook_name IF NOT EXISTS FOR (h:HookPattern) REQUIRE h.name IS UNIQUE",
    "CREATE CONSTRAINT framework_name IF NOT EXISTS FOR (f:ContentFramework) REQUIRE f.name IS UNIQUE",
    "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
]

EXAMPLE_QUERIES = {
    "common_hooks_by_platform": """
MATCH (c:Creator)-[:USES]->(h:HookPattern)
MATCH (c)-[:USES]->(f:ContentFramework)-[:SUITABLE_FOR]->(ct:ContentType {platform: $platform})
WHERE toLower($topic) IN [k IN coalesce(c.keywords, []) | toLower(k)]
   OR exists((:Topic {name: $topic})-[:CONNECTED_TO]->(c))
RETURN h.name AS hook, count(*) AS frequency
ORDER BY frequency DESC
LIMIT 10
""".strip(),
    "creator_style_profile": """
MATCH (c:Creator {name: $creator})-[:USES]->(node)
WHERE node:HookPattern OR node:Tone OR node:SentenceStructure OR node:ContentFramework
RETURN labels(node)[0] AS type, node.name AS name, node
""".strip(),
    "framework_for_content_type": """
MATCH (f:ContentFramework)-[:SUITABLE_FOR]->(ct:ContentType {name: $content_type})
RETURN f.name AS framework, f.steps AS steps
ORDER BY size(coalesce(f.steps, [])) DESC
""".strip(),
}
