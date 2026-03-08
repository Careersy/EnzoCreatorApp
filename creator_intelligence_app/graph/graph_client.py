"""Graph abstraction client backed by local JSON and SQLite mirror."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from creator_intelligence_app.app.config.settings import SETTINGS
from creator_intelligence_app.app.db.database import Database
from creator_intelligence_app.graph.graph_queries import extract_topic_hint, infer_relation_from_query

try:
    from neo4j import GraphDatabase  # type: ignore
except ImportError:  # pragma: no cover
    GraphDatabase = None


class GraphClient:
    def __init__(self, db: Database, graph_json_path: Path) -> None:
        self.db = db
        self.graph_json_path = graph_json_path
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self.neo4j_driver = None
        self.neo4j_database = SETTINGS.neo4j_database
        self._neo4j_last_error = ""

        if GraphDatabase is not None and SETTINGS.neo4j_enabled:
            self.neo4j_driver = GraphDatabase.driver(
                SETTINGS.neo4j_uri,
                auth=(SETTINGS.neo4j_username, SETTINGS.neo4j_password),
            )

    def close(self) -> None:
        if self.neo4j_driver is not None:
            self.neo4j_driver.close()
            self.neo4j_driver = None

    def __del__(self) -> None:  # pragma: no cover
        try:
            self.close()
        except Exception:
            pass

    def verify_connectivity(self) -> dict[str, Any]:
        if self.neo4j_driver is None:
            return {
                "connected": False,
                "mode": "local_json",
                "reason": "Neo4j environment variables not configured or driver unavailable.",
            }

        try:
            self.neo4j_driver.verify_connectivity()
            with self.neo4j_driver.session(database=self.neo4j_database) as session:
                session.run("RETURN 1").single()
            return {
                "connected": True,
                "mode": "neo4j",
                "database": self.neo4j_database,
            }
        except Exception as exc:  # pragma: no cover
            self._neo4j_last_error = str(exc)
            return {
                "connected": False,
                "mode": "neo4j",
                "database": self.neo4j_database,
                "error": str(exc),
            }

    def _neo4j_strongest_hooks(self, limit: int = 10) -> list[dict[str, Any]]:
        if self.neo4j_driver is None:
            return []
        query = """
MATCH (:Creator)-[:USES_TEMPLATE]->(h)
RETURN coalesce(h.name, h.node_id, elementId(h)) AS name, count(*) AS frequency
ORDER BY frequency DESC
LIMIT $limit
"""
        try:
            with self.neo4j_driver.session(database=self.neo4j_database) as session:
                rows = session.run(query, {"limit": limit}).data()
            return [
                {
                    "id": row.get("name"),
                    "name": row.get("name"),
                    "type": "Template",
                    "frequency": row.get("frequency", 0),
                }
                for row in rows
            ]
        except Exception:  # pragma: no cover
            return []

    def _neo4j_creator_patterns(
        self,
        relation_type: str,
        topic: str | None = None,
        platform: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        if self.neo4j_driver is None:
            return []
        query = """
MATCH (c:Creator)-[r]->(p)
WHERE type(r) = $relation
  AND ($topic IS NULL OR toLower(coalesce(c.name, '')) CONTAINS toLower($topic)
       OR toLower(coalesce(p.name, '')) CONTAINS toLower($topic))
  AND ($platform IS NULL OR toLower(toString(p)) CONTAINS toLower($platform)
       OR toLower(toString(r)) CONTAINS toLower($platform))
RETURN c.name AS creator,
       coalesce(p.name, p.node_id, elementId(p)) AS pattern,
       head(labels(p)) AS pattern_type,
       type(r) AS relation,
       properties(r) AS edge
LIMIT $limit
"""
        try:
            with self.neo4j_driver.session(database=self.neo4j_database) as session:
                rows = session.run(
                    query,
                    {
                        "relation": relation_type,
                        "topic": topic,
                        "platform": platform,
                        "limit": limit,
                    },
                ).data()
            return rows
        except Exception:  # pragma: no cover
            return []

    def load_graph(self) -> dict[str, Any]:
        if not self.graph_json_path.exists():
            return {"loaded": False, "reason": f"Missing graph file: {self.graph_json_path}"}

        payload, flat_nodes, edges, graph_hash = self._load_local_graph_payload()

        self.db.reset_graph_tables()
        self.db.bulk_insert_graph_nodes(flat_nodes)
        self.db.bulk_insert_graph_edges(edges)

        self._nodes = {node["id"]: node for node in flat_nodes}
        self._edges = [e for e in edges if isinstance(e, dict)]

        return {
            "loaded": True,
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "graph_hash": graph_hash,
            "meta": payload.get("meta", {}),
        }

    def _load_local_graph_payload(self) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
        raw_text = self.graph_json_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        node_groups = payload.get("nodes", {})
        flat_nodes: list[dict[str, Any]] = []

        for _group, items in node_groups.items():
            for item in items:
                if isinstance(item, dict) and item.get("id"):
                    flat_nodes.append(item)

        edges = [e for e in payload.get("edges", []) if isinstance(e, dict) and e.get("source") and e.get("target")]
        graph_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        return payload, flat_nodes, edges, graph_hash

    @staticmethod
    def _chunks(items: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
        return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    @staticmethod
    def _sanitize_relationship_type(rel_type: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_]", "_", (rel_type or "RELATED").upper())
        if not cleaned:
            cleaned = "RELATED"
        if cleaned[0].isdigit():
            cleaned = f"R_{cleaned}"
        return cleaned

    def import_local_graph_to_neo4j(
        self,
        clear_existing: bool = False,
        dry_run: bool = False,
        force: bool = False,
        batch_size: int = 50,
    ) -> dict[str, Any]:
        if self.neo4j_driver is None:
            return {
                "imported": False,
                "reason": "Neo4j is not configured.",
                "connectivity": self.verify_connectivity(),
            }

        load_status = self.load_graph()
        if not load_status.get("loaded"):
            return {
                "imported": False,
                "reason": load_status.get("reason", "Failed to load local graph file."),
                "connectivity": self.verify_connectivity(),
            }

        payload, flat_nodes, edges, graph_hash = self._load_local_graph_payload()
        batch_size = max(10, min(int(batch_size or 50), 500))

        last_sync = self.db.get_setting("neo4j_graph_sync") or {}
        previous_hash = str(last_sync.get("graph_hash", ""))
        unchanged = previous_hash == graph_hash

        plan = {
            "database": self.neo4j_database,
            "graph_hash": graph_hash,
            "previous_graph_hash": previous_hash or None,
            "unchanged_since_last_import": unchanged,
            "nodes_to_process": len(flat_nodes),
            "edges_to_process": len(edges),
            "batch_size": batch_size,
            "clear_existing": clear_existing,
            "force": force,
        }

        if dry_run:
            return {
                "imported": False,
                "dry_run": True,
                "would_import": force or clear_existing or not unchanged,
                "plan": plan,
                "connectivity": self.verify_connectivity(),
            }

        if unchanged and not force and not clear_existing:
            return {
                "imported": False,
                "skipped": True,
                "reason": "Local graph is unchanged since the last Neo4j import.",
                "plan": plan,
                "connectivity": self.verify_connectivity(),
            }

        try:
            with self.neo4j_driver.session(database=self.neo4j_database) as session:
                session.run(
                    "CREATE CONSTRAINT entity_node_id IF NOT EXISTS "
                    "FOR (n:Entity) REQUIRE n.node_id IS UNIQUE"
                ).consume()

                if clear_existing:
                    session.run("MATCH (n) DETACH DELETE n").consume()
                    session.run(
                        "CREATE CONSTRAINT entity_node_id IF NOT EXISTS "
                        "FOR (n:Entity) REQUIRE n.node_id IS UNIQUE"
                    ).consume()

                node_query = """
UNWIND $rows AS row
MERGE (n:Entity {node_id: row.node_id})
SET n.name = row.name,
    n.node_type = row.node_type,
    n.payload_json = row.payload_json
FOREACH (_ IN CASE WHEN row.is_creator THEN [1] ELSE [] END | SET n:Creator)
"""

                nodes_upserted = 0
                node_rows: list[dict[str, Any]] = []
                for node in flat_nodes:
                    node_rows.append(
                        {
                            "node_id": node["id"],
                            "name": node.get("name"),
                            "node_type": node.get("type", "Unknown"),
                            "payload_json": json.dumps(node),
                            "is_creator": str(node.get("type", "")).lower() == "creator",
                        }
                    )
                for batch in self._chunks(node_rows, batch_size):
                    session.run(
                        node_query,
                        {"rows": batch},
                    ).consume()
                    nodes_upserted += len(batch)

                edge_upserted = 0
                edges_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for edge in edges:
                    rel = self._sanitize_relationship_type(str(edge.get("type", "RELATED")))
                    props = {k: v for k, v in edge.items() if k not in {"source", "target", "type"}}
                    edges_by_type[rel].append(
                        {
                            "source_id": edge["source"],
                            "target_id": edge["target"],
                            "props": props,
                        }
                    )

                for rel, rel_rows in edges_by_type.items():
                    rel_query = f"""
UNWIND $rows AS row
MATCH (s:Entity {{node_id: row.source_id}})
MATCH (t:Entity {{node_id: row.target_id}})
MERGE (s)-[r:{rel}]->(t)
SET r += row.props
"""
                    for batch in self._chunks(rel_rows, batch_size):
                        session.run(rel_query, {"rows": batch}).consume()
                        edge_upserted += len(batch)

                counts = session.run(
                    """
MATCH (n) WITH count(n) AS nodes
MATCH ()-[r]->() RETURN nodes, count(r) AS edges
"""
                ).single()
                self.db.upsert_setting(
                    "neo4j_graph_sync",
                    {
                        "graph_hash": graph_hash,
                        "imported_nodes": nodes_upserted,
                        "imported_edges": edge_upserted,
                        "database": self.neo4j_database,
                        "clear_existing": clear_existing,
                        "batch_size": batch_size,
                    },
                )
                return {
                    "imported": True,
                    "mode": "neo4j",
                    "database": self.neo4j_database,
                    "local_nodes_processed": nodes_upserted,
                    "local_edges_processed": edge_upserted,
                    "neo4j_total_nodes": int(counts["nodes"]),
                    "neo4j_total_edges": int(counts["edges"]),
                    "graph_hash": graph_hash,
                    "batch_size": batch_size,
                    "connectivity": self.verify_connectivity(),
                }
        except Exception as exc:
            self._neo4j_last_error = str(exc)
            return {
                "imported": False,
                "mode": "neo4j",
                "database": self.neo4j_database,
                "error": str(exc),
                "connectivity": self.verify_connectivity(),
            }

    def _ensure_loaded(self) -> None:
        if self._nodes and self._edges:
            return
        self.load_graph()

    def strongest_hook_patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        self._ensure_loaded()
        freq = Counter()
        for edge in self._edges:
            if edge.get("type") == "USES_TEMPLATE":
                freq[edge.get("target")] += 1

        node_lookup = self.db.graph_node_lookup(list(freq.keys()))
        out = []
        for node_id, count in freq.most_common(limit):
            node = node_lookup.get(node_id, {})
            out.append(
                {
                    "id": node_id,
                    "name": node.get("name") or node_id,
                    "type": node.get("node_type", "Unknown"),
                    "frequency": count,
                }
            )
        return out

    def creator_patterns(
        self,
        topic: str | None = None,
        platform: str | None = None,
        relation_type: str = "USES_TEMPLATE",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        self._ensure_loaded()
        matches = []

        node_lookup = {nid: node for nid, node in self._nodes.items()}
        for edge in self._edges:
            if edge.get("type") != relation_type:
                continue

            source = node_lookup.get(edge.get("source"), {})
            target = node_lookup.get(edge.get("target"), {})
            if topic:
                t = topic.lower()
                source_text = json.dumps(source).lower()
                target_text = json.dumps(target).lower()
                if t not in source_text and t not in target_text:
                    continue

            if platform:
                if platform.lower() not in json.dumps(edge).lower() and platform.lower() not in json.dumps(target).lower():
                    continue

            matches.append(
                {
                    "creator": source.get("name", edge.get("source")),
                    "pattern": target.get("name", edge.get("target")),
                    "pattern_type": target.get("type", target.get("node_type", "Unknown")),
                    "relation": relation_type,
                    "edge": edge,
                }
            )

        return matches[:limit]

    def query_natural_language(self, query: str, limit: int = 25) -> dict[str, Any]:
        relation = infer_relation_from_query(query)
        topic_hint = extract_topic_hint(query)
        records = self._neo4j_creator_patterns(
            relation_type=relation,
            topic=topic_hint,
            limit=limit,
        )
        if not records:
            records = self.creator_patterns(topic=topic_hint, relation_type=relation, limit=limit)

        if not records and relation != "COVERS":
            records = self._neo4j_creator_patterns(
                relation_type="COVERS",
                topic=topic_hint,
                limit=limit,
            )
            if not records:
                records = self.creator_patterns(topic=topic_hint, relation_type="COVERS", limit=limit)

        strongest_hooks = self._neo4j_strongest_hooks(limit=8)
        if not strongest_hooks:
            strongest_hooks = self.strongest_hook_patterns(limit=8)

        return {
            "relation": relation,
            "topic_hint": topic_hint,
            "records": records,
            "strongest_hooks": strongest_hooks,
            "connectivity": self.verify_connectivity(),
        }

    def pattern_library(
        self,
        relation_type: str = "USES_TEMPLATE",
        creator: str | None = None,
        topic: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        relation = str(relation_type or "USES_TEMPLATE").upper()
        records = self._neo4j_creator_patterns(
            relation_type=relation,
            topic=topic,
            limit=limit,
        )
        if not records:
            records = self.creator_patterns(
                topic=topic,
                relation_type=relation,
                limit=limit,
            )

        creator_filter = str(creator or "").strip().lower()
        if creator_filter:
            records = [r for r in records if creator_filter in str(r.get("creator", "")).lower()]

        creators = sorted({str(r.get("creator", "")).strip() for r in records if str(r.get("creator", "")).strip()})
        patterns = sorted({str(r.get("pattern", "")).strip() for r in records if str(r.get("pattern", "")).strip()})
        relation_counts: dict[str, int] = defaultdict(int)
        for row in records:
            relation_counts[str(row.get("relation", relation))] += 1

        strongest_hooks = self._neo4j_strongest_hooks(limit=12) if relation == "USES_TEMPLATE" else []
        if relation == "USES_TEMPLATE" and not strongest_hooks:
            strongest_hooks = self.strongest_hook_patterns(limit=12)

        return {
            "relation": relation,
            "topic_hint": topic,
            "creator_filter": creator,
            "records": records,
            "summary": {
                "record_count": len(records),
                "creator_count": len(creators),
                "pattern_count": len(patterns),
                "relation_breakdown": relation_counts,
            },
            "creators": creators,
            "strongest_hooks": strongest_hooks,
            "connectivity": self.verify_connectivity(),
        }

    def top_nodes_by_type(self, node_type: str, limit: int = 20) -> list[dict[str, Any]]:
        self._ensure_loaded()
        out = []
        for node in self._nodes.values():
            if str(node.get("type", "")).lower() == node_type.lower():
                out.append(node)
            if len(out) >= limit:
                break
        return out

    def creator_profile(self, creator_name: str) -> dict[str, Any]:
        self._ensure_loaded()
        creator_nodes = [n for n in self._nodes.values() if n.get("type") == "Creator" and str(n.get("name", "")).lower() == creator_name.lower()]
        if not creator_nodes:
            return {"creator": creator_name, "patterns": []}

        creator = creator_nodes[0]
        patterns = []
        for edge in self._edges:
            if edge.get("source") != creator.get("id"):
                continue
            target = self._nodes.get(edge.get("target"), {})
            patterns.append(
                {
                    "relation": edge.get("type"),
                    "target": target.get("name", edge.get("target")),
                    "target_type": target.get("type", "Unknown"),
                }
            )

        return {
            "creator": creator,
            "patterns": patterns,
        }

    def list_creators(self, limit: int = 50) -> list[str]:
        self._ensure_loaded()
        names = [
            str(node.get("name"))
            for node in self._nodes.values()
            if str(node.get("type", "")).lower() == "creator" and node.get("name")
        ]
        names = sorted(set(names))
        return names[:limit]

    def creator_mixer(
        self,
        creator_weights: list[dict[str, Any]],
        relation_types: list[str] | None = None,
        limit_per_creator: int = 20,
    ) -> dict[str, Any]:
        self._ensure_loaded()
        rel_types = [str(r) for r in (relation_types or ["USES_TEMPLATE", "USES_FRAMEWORK", "USES_TONE"])]
        normalized: list[dict[str, Any]] = []
        total = sum(float(item.get("weight", 0)) for item in creator_weights) or 1.0
        for item in creator_weights:
            normalized.append(
                {
                    "creator": str(item.get("creator", "")).strip(),
                    "weight": round(float(item.get("weight", 0)) / total, 3),
                }
            )

        out_records: list[dict[str, Any]] = []
        for item in normalized:
            name = item["creator"]
            if not name:
                continue
            profile = self.creator_profile(name)
            patterns = list(profile.get("patterns", []))[:limit_per_creator]
            for p in patterns:
                if str(p.get("relation")) not in rel_types:
                    continue
                out_records.append(
                    {
                        "creator": name,
                        "weight": item["weight"],
                        "relation": p.get("relation"),
                        "pattern": p.get("target"),
                        "pattern_type": p.get("target_type"),
                    }
                )

        # Weighted ranking favors the dominant creator while preserving diversity.
        out_records.sort(key=lambda r: (float(r.get("weight", 0)), str(r.get("relation", ""))), reverse=True)
        return {
            "creator_weights": normalized,
            "records": out_records,
        }

    def pattern_summary(self) -> dict[str, list[str]]:
        self._ensure_loaded()
        rel_map: dict[str, set[str]] = defaultdict(set)
        for edge in self._edges:
            source = self._nodes.get(edge.get("source"), {})
            target = self._nodes.get(edge.get("target"), {})
            if source.get("type") == "Creator":
                rel_map[edge.get("type", "RELATED")].add(target.get("name", edge.get("target", "")))

        return {rel: sorted(list(items))[:20] for rel, items in rel_map.items()}

    def connection_status(self) -> dict[str, Any]:
        status = self.verify_connectivity()
        if self._neo4j_last_error and "error" not in status:
            status["error"] = self._neo4j_last_error
        return status

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    def learn_hook_engagement(self, hook_text: str, platform: str, avg_score: float, event_count: int) -> dict[str, Any]:
        hook = (hook_text or "").strip()
        plat = (platform or "LinkedIn").strip()
        if not hook:
            return {"updated": False, "reason": "Missing hook text"}

        hook_node_id = f"hook::{self._slug(hook) or 'unknown'}"
        engagement_node_id = f"engagement::{self._slug(plat) or 'platform'}"
        hook_payload = {
            "id": hook_node_id,
            "name": hook,
            "type": "HookPattern",
            "learned": True,
        }
        engagement_payload = {
            "id": engagement_node_id,
            "name": f"{plat} Engagement",
            "type": "Engagement",
            "platform": plat,
            "learned": True,
        }
        edge_payload = {
            "source": hook_node_id,
            "target": engagement_node_id,
            "type": "DRIVES_ENGAGEMENT",
            "avg_score": float(avg_score),
            "event_count": int(event_count),
            "platform": plat,
        }

        with self.db.session() as conn:
            conn.execute(
                "DELETE FROM creator_edges WHERE source_node_id = ? AND target_node_id = ? AND edge_type = ?",
                (hook_node_id, engagement_node_id, "DRIVES_ENGAGEMENT"),
            )
            for node in (hook_payload, engagement_payload):
                exists = conn.execute("SELECT id FROM creator_nodes WHERE node_id = ?", (node["id"],)).fetchone()
                if exists:
                    conn.execute(
                        "UPDATE creator_nodes SET node_type = ?, name = ?, properties_json = ? WHERE node_id = ?",
                        (node["type"], node["name"], json.dumps(node), node["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO creator_nodes (node_id, node_type, name, properties_json) VALUES (?, ?, ?, ?)",
                        (node["id"], node["type"], node["name"], json.dumps(node)),
                    )
            conn.execute(
                """
INSERT INTO creator_edges (source_node_id, target_node_id, edge_type, properties_json)
VALUES (?, ?, ?, ?)
""",
                (hook_node_id, engagement_node_id, "DRIVES_ENGAGEMENT", json.dumps(edge_payload)),
            )

        self._nodes[hook_node_id] = hook_payload
        self._nodes[engagement_node_id] = engagement_payload
        self._edges.append(edge_payload)

        neo4j_updated = False
        if self.neo4j_driver is not None:
            try:
                with self.neo4j_driver.session(database=self.neo4j_database) as session:
                    session.run(
                        """
MERGE (h:Entity:HookPattern {node_id: $hook_id})
SET h.name = $hook_name, h.learned = true
MERGE (e:Entity:Engagement {node_id: $engagement_id})
SET e.name = $engagement_name, e.platform = $platform, e.learned = true
MERGE (h)-[r:DRIVES_ENGAGEMENT]->(e)
SET r.avg_score = $avg_score, r.event_count = $event_count, r.platform = $platform
""",
                        {
                            "hook_id": hook_node_id,
                            "hook_name": hook,
                            "engagement_id": engagement_node_id,
                            "engagement_name": f"{plat} Engagement",
                            "platform": plat,
                            "avg_score": float(avg_score),
                            "event_count": int(event_count),
                        },
                    ).consume()
                neo4j_updated = True
            except Exception:  # pragma: no cover
                neo4j_updated = False

        return {
            "updated": True,
            "hook_node_id": hook_node_id,
            "engagement_node_id": engagement_node_id,
            "neo4j_updated": neo4j_updated,
        }
