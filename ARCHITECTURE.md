# ARCHITECTURE: Creator Intelligence Web App

## System Overview

A private, local-first web app that ingests creator/user content, builds a hybrid retrieval context, and generates/re-writes content with user voice priority.

## Components

### 1) Web Layer

- Single-page local UI (`Upload/Ingest`, `Knowledge Explorer`, `Rewrite Studio`, `Draft Generator`, `Long-Form Expander`, `Content Planner`, `Settings`)
- Served by FastAPI templates/static assets

### 2) API Layer

Main endpoints:
- `POST /api/ingest/file`
- `POST /api/ingest/text`
- `GET /api/sources`
- `POST /api/style/extract`
- `POST /api/query/graph`
- `POST /api/blueprint/build`
- `POST /api/rewrite`
- `POST /api/generate`
- `POST /api/expand`
- `POST /api/plan`
- `POST /api/compare-style`
- `POST /api/export/markdown`
- `POST /api/integrations/notion/sync` (stub in Phase 1)

### 3) Service Layer

- `IngestionService`: parse files/text, classify, chunk, persist
- `GraphService`: load/query creator knowledge graph
- `SemanticRetriever`: local semantic retrieval over chunks
- `HybridRetriever`: graph + semantic + metadata + style-match composition
- `StyleProfiler`: extract user voice profile from tagged user content
- `BlueprintBuilder`: produce `Use/Prefer/Avoid/Unclear` style blueprint
- `AntiAIDetector`: detect generic AI language risk
- `GenerationService`: rewrite/generate/expand using retrieval-first pipeline
- `PlannerService`: topic maps, angles, hooks, weekly calendars

### 4) Storage Layer

- SQLite `data/app.db`:
  - structured records, chunks, profiles, drafts, phrase rules, settings
- Local files:
  - `data/uploads/` raw inputs
  - `data/exports/` markdown exports
  - `data/indexes/` optional local index files
- Local graph source:
  - `knowledge-graph.json`

## Data Model

### SQLite tables

1. `sources`
- `id`, `title`, `source_type`, `author_type`, `platform`, `content_type`
- `is_mine`, `is_creator_sample`, `is_draft`, `is_published`
- `source_path`, `raw_text`, `metadata_json`, `created_at`

2. `source_chunks`
- `id`, `source_id`, `chunk_index`, `chunk_text`, `token_estimate`
- `embedding_json`, `platform`, `content_type`, `author_type`, `created_at`

3. `style_profiles`
- `id`, `profile_name`, `author_scope`, `metrics_json`, `created_at`

4. `drafts`
- `id`, `draft_type`, `platform`, `goal`, `input_text`, `output_text`
- `hooks_json`, `cta_json`, `scores_json`, `notes_json`, `created_at`

5. `phrase_rules`
- `id`, `rule_type` (`banned|overused|preferred|signature`), `phrase`, `weight`

6. `settings`
- `id`, `key`, `value_json`

7. `creator_nodes`
- `id`, `node_id`, `node_type`, `name`, `properties_json`

8. `creator_edges`
- `id`, `source_node_id`, `target_node_id`, `edge_type`, `properties_json`

## Retrieval Architecture

### Query Flow

1. Parse user request and task context
2. Graph retrieval for creator patterns
3. Semantic retrieval for nearest user/creator examples
4. Metadata filtering and ranking
5. User-style nearest neighbor selection
6. Compose retrieval package
7. Build style blueprint

### Retrieval Outputs

- `creator_patterns`: hooks, frameworks, tone markers, CTA styles
- `user_examples`: closest writing samples from user corpus
- `anti_patterns`: banned/overused/generic phrase risks
- `style_features`: inferred cadence, syntax tendencies

## Style Fidelity Architecture

### Profiles

1. `UserVoiceProfile` (primary)
2. `CreatorPatternProfile` (secondary)
3. `BlendedBlueprint`:
- `Use`
- `Prefer`
- `Avoid`
- `Unclear`

### Scoring

- `style_match_to_user`
- `creator_structure_alignment`
- `platform_fit`
- `ai_genericity_risk`
- `readability`

### Rewrite/Generation policy

- hard requirement: retrieval + blueprint before any generation call
- post-generation check: anti-generic detector + phrase rule enforcement
- optional revision pass if genericity risk high

## Ingestion Architecture

### File ingestion

1. store original file in `data/uploads`
2. parse text (`pypdf` fallback for PDFs)
3. normalize and chunk
4. persist `sources` and `source_chunks`
5. compute/store local embedding vector
6. update style inputs if user-authored

### Paste ingestion

1. capture text + tags in UI
2. same normalization/chunk pipeline
3. source type recorded as `pasted_text`

## Privacy & Security Model

- private-by-default local operation
- no background cloud sync
- optional integrations disabled unless configured
- credentials via env vars only
- explicit boundaries between core local data and optional external services

## Deployment Model

- Phase 1: local run (`uvicorn`) on `localhost`
- Optional later:
  - Dockerized local/remote deployment
  - self-hosted VM/container
  - optional auth gateway

## Extensibility Points

- swap semantic embedding implementation
- add Neo4j/FalkorDB adapters
- add multi-user auth in remote mode
- add richer notion/github sync modules

