"""SQLite database bootstrap and repository helpers."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    col_names = {row[1] for row in cols}
    if column not in col_names:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db(db_path: Path) -> None:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    source_type TEXT,
    source_hash TEXT,
    author_type TEXT,
    platform TEXT,
    content_type TEXT,
    is_mine INTEGER DEFAULT 0,
    is_creator_sample INTEGER DEFAULT 0,
    is_draft INTEGER DEFAULT 0,
    is_published INTEGER DEFAULT 0,
    source_path TEXT,
    raw_text TEXT,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_estimate INTEGER DEFAULT 0,
    embedding_json TEXT,
    platform TEXT,
    content_type TEXT,
    author_type TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS style_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,
    author_scope TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_type TEXT NOT NULL,
    platform TEXT,
    goal TEXT,
    input_text TEXT,
    output_text TEXT,
    hooks_json TEXT,
    cta_json TEXT,
    scores_json TEXT,
    notes_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phrase_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type TEXT NOT NULL,
    phrase TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value_json TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS creator_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    name TEXT,
    properties_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS creator_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    properties_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0,
    payload_json TEXT,
    result_json TEXT,
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    platform TEXT,
    topic TEXT,
    hook_text TEXT,
    creator_name TEXT,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    engagement_score REAL DEFAULT 0,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hook_performance_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hook_text TEXT NOT NULL,
    platform TEXT NOT NULL,
    event_count INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_shares INTEGER DEFAULT 0,
    total_engagement_score REAL DEFAULT 0,
    avg_engagement_score REAL DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hook_text, platform)
);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON source_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_author_type ON source_chunks(author_type);
CREATE INDEX IF NOT EXISTS idx_chunks_platform ON source_chunks(platform);
CREATE INDEX IF NOT EXISTS idx_edges_type ON creator_edges(edge_type);
CREATE INDEX IF NOT EXISTS idx_perf_platform ON performance_events(platform);
CREATE INDEX IF NOT EXISTS idx_perf_hook ON performance_events(hook_text);
"""
        )
        _ensure_column(conn, "sources", "source_hash", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(source_hash)")
        conn.commit()
    finally:
        conn.close()


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        conn = _connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add_source(self, payload: dict[str, Any]) -> int:
        with self.session() as conn:
            cur = conn.execute(
                """
INSERT INTO sources (
    title, source_type, source_hash, author_type, platform, content_type,
    is_mine, is_creator_sample, is_draft, is_published,
    source_path, raw_text, metadata_json
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
                (
                    payload.get("title"),
                    payload.get("source_type"),
                    payload.get("source_hash"),
                    payload.get("author_type"),
                    payload.get("platform"),
                    payload.get("content_type"),
                    int(payload.get("is_mine", False)),
                    int(payload.get("is_creator_sample", False)),
                    int(payload.get("is_draft", False)),
                    int(payload.get("is_published", False)),
                    payload.get("source_path"),
                    payload.get("raw_text", ""),
                    json.dumps(payload.get("metadata", {})),
                ),
            )
            return int(cur.lastrowid)

    def add_chunks(self, source_id: int, chunks: list[dict[str, Any]]) -> None:
        with self.session() as conn:
            conn.executemany(
                """
INSERT INTO source_chunks (
    source_id, chunk_index, chunk_text, token_estimate,
    embedding_json, platform, content_type, author_type
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""",
                [
                    (
                        source_id,
                        c["chunk_index"],
                        c["chunk_text"],
                        c.get("token_estimate", 0),
                        json.dumps(c.get("embedding", [])),
                        c.get("platform"),
                        c.get("content_type"),
                        c.get("author_type"),
                    )
                    for c in chunks
                ],
            )

    def list_sources(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                """
SELECT id, title, source_type, source_hash, author_type, platform, content_type,
       is_mine, is_creator_sample, is_draft, is_published,
       source_path, created_at
FROM sources
ORDER BY id DESC
LIMIT ?
""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_sources_with_text(self, limit: int = 500) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                """
SELECT *
FROM sources
ORDER BY id DESC
LIMIT ?
""",
                (limit,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.get("metadata_json") or "{}")
            out.append(item)
        return out

    def get_source_by_hash(self, source_hash: str) -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute(
                "SELECT * FROM sources WHERE source_hash = ? ORDER BY id DESC LIMIT 1",
                (source_hash,),
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["metadata"] = json.loads(item.get("metadata_json") or "{}")
        return item

    def get_chunks(
        self,
        author_type: str | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = """
SELECT sc.*, s.title
FROM source_chunks sc
JOIN sources s ON s.id = sc.source_id
WHERE 1=1
"""
        params: list[Any] = []

        if author_type:
            query += " AND sc.author_type = ?"
            params.append(author_type)
        if platform:
            query += " AND sc.platform = ?"
            params.append(platform)
        if content_type:
            query += " AND sc.content_type = ?"
            params.append(content_type)

        query += " ORDER BY sc.id DESC LIMIT ?"
        params.append(limit)

        with self.session() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["embedding"] = json.loads(item.get("embedding_json") or "[]")
            except json.JSONDecodeError:
                item["embedding"] = []
            out.append(item)
        return out

    def get_chunks_for_source(self, source_id: int, limit: int = 2000) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                """
SELECT sc.*, s.title
FROM source_chunks sc
JOIN sources s ON s.id = sc.source_id
WHERE sc.source_id = ?
ORDER BY sc.chunk_index ASC
LIMIT ?
""",
                (source_id, limit),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["embedding"] = json.loads(item.get("embedding_json") or "[]")
            except json.JSONDecodeError:
                item["embedding"] = []
            out.append(item)
        return out

    def get_source_texts(self, is_mine: bool | None = None, limit: int = 300) -> list[str]:
        query = "SELECT raw_text FROM sources WHERE raw_text IS NOT NULL"
        params: list[Any] = []
        if is_mine is not None:
            query += " AND is_mine = ?"
            params.append(int(is_mine))
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self.session() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [str(row[0]) for row in rows if row[0]]

    def delete_chunks_for_source(self, source_id: int) -> None:
        with self.session() as conn:
            conn.execute("DELETE FROM source_chunks WHERE source_id = ?", (source_id,))

    def save_style_profile(self, profile_name: str, author_scope: str, metrics: dict[str, Any]) -> int:
        with self.session() as conn:
            cur = conn.execute(
                """
INSERT INTO style_profiles (profile_name, author_scope, metrics_json)
VALUES (?, ?, ?)
""",
                (profile_name, author_scope, json.dumps(metrics)),
            )
            return int(cur.lastrowid)

    def latest_style_profile(self, author_scope: str = "mine") -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute(
                """
SELECT id, profile_name, author_scope, metrics_json, created_at
FROM style_profiles
WHERE author_scope = ?
ORDER BY id DESC
LIMIT 1
""",
                (author_scope,),
            ).fetchone()
        if not row:
            return None
        record = dict(row)
        record["metrics"] = json.loads(record.get("metrics_json") or "{}")
        return record

    def save_draft(
        self,
        draft_type: str,
        platform: str,
        goal: str,
        input_text: str,
        output_text: str,
        hooks: list[str],
        ctas: list[str],
        scores: dict[str, Any],
        notes: dict[str, Any],
    ) -> int:
        with self.session() as conn:
            cur = conn.execute(
                """
INSERT INTO drafts (
    draft_type, platform, goal, input_text, output_text,
    hooks_json, cta_json, scores_json, notes_json
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
                (
                    draft_type,
                    platform,
                    goal,
                    input_text,
                    output_text,
                    json.dumps(hooks),
                    json.dumps(ctas),
                    json.dumps(scores),
                    json.dumps(notes),
                ),
            )
            return int(cur.lastrowid)

    def add_phrase_rule(self, rule_type: str, phrase: str, weight: float = 1.0) -> int:
        with self.session() as conn:
            cur = conn.execute(
                "INSERT INTO phrase_rules (rule_type, phrase, weight) VALUES (?, ?, ?)",
                (rule_type, phrase, weight),
            )
            return int(cur.lastrowid)

    def list_phrase_rules(self, rule_type: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT id, rule_type, phrase, weight FROM phrase_rules"
        params: list[Any] = []
        if rule_type:
            query += " WHERE rule_type = ?"
            params.append(rule_type)
        with self.session() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def upsert_setting(self, key: str, value: dict[str, Any]) -> None:
        with self.session() as conn:
            conn.execute(
                """
INSERT INTO settings (key, value_json, updated_at)
VALUES (?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=CURRENT_TIMESTAMP
""",
                (key, json.dumps(value)),
            )

    def get_setting(self, key: str) -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute(
                "SELECT value_json FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def reset_graph_tables(self) -> None:
        with self.session() as conn:
            conn.execute("DELETE FROM creator_nodes")
            conn.execute("DELETE FROM creator_edges")

    def bulk_insert_graph_nodes(self, nodes: list[dict[str, Any]]) -> None:
        with self.session() as conn:
            conn.executemany(
                "INSERT INTO creator_nodes (node_id, node_type, name, properties_json) VALUES (?, ?, ?, ?)",
                [
                    (
                        item.get("id"),
                        item.get("type", "Unknown"),
                        item.get("name"),
                        json.dumps(item),
                    )
                    for item in nodes
                ],
            )

    def bulk_insert_graph_edges(self, edges: list[dict[str, Any]]) -> None:
        with self.session() as conn:
            conn.executemany(
                "INSERT INTO creator_edges (source_node_id, target_node_id, edge_type, properties_json) VALUES (?, ?, ?, ?)",
                [
                    (
                        edge.get("source"),
                        edge.get("target"),
                        edge.get("type", "RELATED"),
                        json.dumps(edge),
                    )
                    for edge in edges
                ],
            )

    def graph_edges_by_type(self, edge_type: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                """
SELECT source_node_id, target_node_id, edge_type, properties_json
FROM creator_edges
WHERE edge_type = ?
LIMIT ?
""",
                (edge_type, limit),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["properties"] = json.loads(item.get("properties_json") or "{}")
            out.append(item)
        return out

    def graph_node_lookup(self, node_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not node_ids:
            return {}
        placeholders = ",".join(["?"] * len(node_ids))
        with self.session() as conn:
            rows = conn.execute(
                f"SELECT node_id, node_type, name, properties_json FROM creator_nodes WHERE node_id IN ({placeholders})",
                tuple(node_ids),
            ).fetchall()
        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = dict(row)
            item["properties"] = json.loads(item.get("properties_json") or "{}")
            out[item["node_id"]] = item
        return out

    def upsert_job(
        self,
        job_id: str,
        job_type: str,
        status: str,
        progress: float = 0.0,
        payload: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self.session() as conn:
            conn.execute(
                """
INSERT INTO ingestion_jobs (id, job_type, status, progress, payload_json, result_json, error, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(id) DO UPDATE SET
    status=excluded.status,
    progress=excluded.progress,
    payload_json=excluded.payload_json,
    result_json=excluded.result_json,
    error=excluded.error,
    updated_at=CURRENT_TIMESTAMP
""",
                (
                    job_id,
                    job_type,
                    status,
                    progress,
                    json.dumps(payload or {}),
                    json.dumps(result or {}),
                    error,
                ),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute("SELECT * FROM ingestion_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.get("payload_json") or "{}")
        item["result"] = json.loads(item.get("result_json") or "{}")
        return item

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                "SELECT * FROM ingestion_jobs ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.get("payload_json") or "{}")
            item["result"] = json.loads(item.get("result_json") or "{}")
            out.append(item)
        return out

    def list_creators(self, limit: int = 100) -> list[str]:
        with self.session() as conn:
            rows = conn.execute(
                """
SELECT DISTINCT name
FROM creator_nodes
WHERE lower(node_type) = 'creator' AND name IS NOT NULL
ORDER BY name ASC
LIMIT ?
""",
                (limit,),
            ).fetchall()
        return [str(row[0]) for row in rows if row[0]]

    def add_performance_event(
        self,
        source_id: int | None,
        platform: str,
        topic: str | None,
        hook_text: str,
        creator_name: str | None,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        engagement_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        with self.session() as conn:
            cur = conn.execute(
                """
INSERT INTO performance_events (
    source_id, platform, topic, hook_text, creator_name,
    views, likes, comments, shares, engagement_score, metadata_json
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
                (
                    source_id,
                    platform,
                    topic,
                    hook_text,
                    creator_name,
                    views,
                    likes,
                    comments,
                    shares,
                    float(engagement_score),
                    json.dumps(metadata or {}),
                ),
            )
            return int(cur.lastrowid)

    def upsert_hook_performance(
        self,
        hook_text: str,
        platform: str,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        engagement_score: float,
    ) -> None:
        with self.session() as conn:
            conn.execute(
                """
INSERT INTO hook_performance_stats (
    hook_text, platform, event_count, total_views, total_likes, total_comments,
    total_shares, total_engagement_score, avg_engagement_score, updated_at
)
VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(hook_text, platform) DO UPDATE SET
    event_count = event_count + 1,
    total_views = total_views + excluded.total_views,
    total_likes = total_likes + excluded.total_likes,
    total_comments = total_comments + excluded.total_comments,
    total_shares = total_shares + excluded.total_shares,
    total_engagement_score = total_engagement_score + excluded.total_engagement_score,
    avg_engagement_score = (total_engagement_score + excluded.total_engagement_score) / (event_count + 1),
    updated_at = CURRENT_TIMESTAMP
""",
                (
                    hook_text,
                    platform,
                    views,
                    likes,
                    comments,
                    shares,
                    float(engagement_score),
                    float(engagement_score),
                ),
            )

    def top_performing_hooks(self, platform: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        query = """
SELECT hook_text, platform, event_count, total_views, total_likes, total_comments, total_shares,
       total_engagement_score, avg_engagement_score
FROM hook_performance_stats
WHERE 1=1
"""
        params: list[Any] = []
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        query += " ORDER BY avg_engagement_score DESC, event_count DESC LIMIT ?"
        params.append(limit)
        with self.session() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def recent_performance_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                """
SELECT id, source_id, platform, topic, hook_text, creator_name, views, likes, comments, shares, engagement_score, metadata_json, created_at
FROM performance_events
ORDER BY id DESC
LIMIT ?
""",
                (limit,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.get("metadata_json") or "{}")
            out.append(item)
        return out
