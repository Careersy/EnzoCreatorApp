# PLAN: Creator Intelligence Web App (Local-First)

## 1. Architecture Recommendation

Use a modular local-first architecture with a Python API backend and a browser UI:

1. `Web UI` (local browser) for ingest, explore, rewrite, generate, expand, and planning
2. `API Layer` (FastAPI) exposing ingestion, retrieval, style, and generation endpoints
3. `Service Layer` with clear modules:
   - ingestion
   - graph retrieval
   - semantic retrieval
   - style fidelity engine
   - blueprint builder
   - generation engines
4. `Storage Layer` (private-by-default local data):
   - SQLite for app metadata, chunks, style profiles, drafts, settings
   - local filesystem for uploads/exports
   - graph abstraction over local JSON/SQLite edge tables (with optional Neo4j later)
   - local vector index abstraction (deterministic embedding baseline; pluggable real embeddings)

## 2. Assumptions

1. User runs app on laptop (macOS/Linux/Windows) with Python 3.11+
2. User has a creator graph JSON (already present in repo)
3. OpenAI API key is optional for first run; app has local fallback outputs
4. Notion and GitHub integrations are optional and disabled by default
5. Private mode is default; no outbound sync without explicit configuration
6. First implementation prioritizes LinkedIn + newsletter/blog expansion paths

## 3. Recommended Stack

Backend:
1. Python 3.11
2. FastAPI + Uvicorn
3. Pydantic models for API schemas
4. SQLite (`sqlite3`) for local persistence

Retrieval/AI:
1. Local graph adapter from `knowledge-graph.json`
2. Hybrid retrieval service (graph + semantic + metadata + style-match)
3. Optional OpenAI client (fallback when key missing)
4. Anti-generic detector with rule-based scoring + phrase lists

Frontend:
1. Local-first single-page HTML/CSS/JS served by FastAPI static/templates
2. Tab-based UI for all required workflows

DevOps:
1. `.env` config
2. Dockerfile + docker-compose for optional containerized local run
3. `unittest` test suite for core services

## 4. Project Structure

```text
creator_intelligence_app/
  app/
    api/
    services/
    models/
    schemas/
    config/
    db/
    web/
      static/
      templates/
  ingestion/
  graph/
  retrieval/
  style/
  generation/
  integrations/
  data/
    uploads/
    exports/
    indexes/
  tests/
  scripts/
  docs/
```

## 5. Schema Design (Phase 1)

SQLite core tables:
1. `sources` - uploaded/pasted source records
2. `source_chunks` - normalized text chunks with metadata
3. `style_profiles` - user style profile snapshots and metrics
4. `drafts` - generated/rewritten/expanded outputs and notes
5. `phrase_rules` - banned/overused/preferred/signature phrases
6. `settings` - model, privacy, weighting, integration flags
7. `creator_nodes` / `creator_edges` - local graph mirror for traversal

Primary entities supported:
1. Creator graph entities (creator, hook pattern, tone, framework, persuasion, CTA, topic, content type)
2. User style entities (phrase patterns, cadence, tone markers, avoided phrases, CTA tendencies)

## 6. Retrieval Design

Hybrid retrieval pipeline:
1. Parse task intent + constraints (platform, goal, audience, format)
2. Graph retrieval:
   - top creator hooks/frameworks/patterns for task context
3. Semantic retrieval:
   - nearest chunks from user corpus and creator samples
4. Metadata filters:
   - platform, author, source type, published/draft, short/long-form
5. Style-match retrieval:
   - closest user examples by rhythm/vocabulary heuristics
6. Compose retrieval bundle -> style blueprint builder

## 7. Ingestion Workflow

1. Upload or paste content (`PDF`, `TXT`, `MD`, direct paste)
2. Parse and normalize text
3. Extract metadata tags:
   - mine/creator
   - draft/published
   - platform/content type
4. Chunk content for retrieval
5. Persist source + chunks to SQLite
6. Index chunks in local semantic index
7. If tagged `mine`, feed style profiler update queue

## 8. Style-Fidelity Strategy (Primary Requirement)

User-voice-first blending rule:
1. User voice profile (primary)
2. Creator pattern profile (secondary)
3. Platform conventions (tertiary)

Key style features extracted:
1. sentence and paragraph length distributions
2. punctuation and rhetorical question habits
3. signature phrases, preferred verbs, transition markers
4. CTA tendencies
5. anti-patterns and AI-sounding phrase risk

Scoring per output:
1. `user_style_match` (0-100)
2. `creator_alignment` (0-100)
3. `platform_fit` (0-100)
4. `ai_genericity_risk` (0-100, lower better)

Generation policy:
1. Never generate without retrieval + blueprint
2. Run anti-generic checks post-draft
3. Auto-revise once when genericity exceeds threshold

## 9. Privacy Model

1. Default local mode only
2. Files and database stored under local `data/`
3. API keys loaded from `.env`, never hardcoded
4. External integrations opt-in and explicit
5. Export is local markdown by default
6. Notion/GitHub sync paths isolated in optional integration modules

## 10. Phased Roadmap

Phase 1 (implemented now):
1. Local web app tabs
2. Ingestion (PDF/text/paste) + tagging
3. Local graph loading + queries
4. User style extraction
5. Rewrite studio
6. Draft generator (LinkedIn-first)
7. Basic expansion (newsletter/blog/article/substack)
8. Markdown export

Phase 2:
1. Stronger semantic embeddings
2. richer style scoring + side-by-side comparisons
3. saved blueprints and weighting controls

Phase 3:
1. content planner enhancements
2. series generation + calendar workflows

Phase 4:
1. optional Notion sync
2. optional GitHub export workflows
3. remote deployment docs and container hardening

## Stage Rule Compliance

This file completes Stage 1 planning. Implementation starts immediately after this document set.
