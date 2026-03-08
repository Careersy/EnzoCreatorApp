# Creator Intelligence App (Local-First)

Private-by-default, open-source web app for creator-informed content workflows with user-voice style fidelity as the top priority.

## Stage Deliverables

Planning documents:
- `PLAN.md`
- `ARCHITECTURE.md`
- `TASKLIST.md`

Implemented Phase 1 MVP:
- Local web app on `localhost`
- File/text ingestion with tagging
- Content hash dedupe + optional duplicate override
- Background file ingestion jobs
- Reindex endpoint for retrieval refresh
- Creator graph querying from local `knowledge-graph.json`
- User style profile extraction
- Retrieval-first rewrite/generate/expand flows with anti-generic cleanup
- Creator Style Mixer (weighted creator blend + user voice)
- Performance learning layer (ingest metrics, learn top hooks, feed blueprint)
- Basic content planner
- Topic map, calendar planning, and repurposing pipeline workflows
- Markdown export
- Optional Notion/GitHub integrations
- Docker setup and core tests
- Phase 4 hardening: optional API auth, security headers, CORS controls, upload limits, production compose profile

## Project Layout

```text
creator_intelligence_app/
  app/
    api/routes.py
    services/
      bootstrap.py
      content_service.py
      llm_client.py
    db/database.py
    schemas/api.py
    config/settings.py
    web/
      templates/index.html
      static/app.js
      static/styles.css
    main.py
  ingestion/
  graph/
  retrieval/
  style/
  generation/
  integrations/
  data/
  tests/
  docs/SETUP.md
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn creator_intelligence_app.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Core API Actions

- `POST /api/ingest/file`
- `POST /api/ingest/text`
- `GET /api/sources`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/reindex`
- `POST /api/style/extract`
- `POST /api/query/graph`
- `POST /api/blueprint/build`
- `POST /api/rewrite`
- `POST /api/generate`
- `POST /api/expand`
- `GET /api/model/status`
- `GET /api/creators`
- `POST /api/style/mix`
- `POST /api/performance/ingest`
- `POST /api/performance/summary`
- `POST /api/plan`
- `POST /api/plan/topic-map`
- `POST /api/plan/calendar`
- `POST /api/repurpose`
- `POST /api/compare-style`
- `POST /api/export/markdown`
- `POST /api/neo4j/import`
- `POST /api/integrations/notion/sync`
- `POST /api/integrations/github/export`

Neo4j import options (`/api/neo4j/import`):
- `dry_run`: return import plan only (no writes)
- `force`: import even if local graph hash is unchanged
- `batch_size`: write batch size (10-500), default `50`
- hash-based skip is enabled by default to protect free-tier limits

Ingestion options (`/api/ingest/file` and `/api/ingest/text`):
- `allow_duplicate`: bypass content-hash dedupe
- `run_in_background` (file ingest): queue ingestion job and poll `/api/jobs/{job_id}`

Model connection notes:
- Supports OpenAI and Anthropic.
- Set `LLM_PROVIDER=auto|openai|anthropic`.
- Set `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` to enable real model generation.
- `OPENAI_MODEL` and `ANTHROPIC_MODEL` control provider defaults.
- `AVAILABLE_MODELS` controls UI dropdown options.
- Optional `OPENAI_BASE_URL` supports OpenAI-compatible gateways.
- Vector backend: `VECTOR_BACKEND=local|chroma` and `CHROMA_PERSIST_DIR=...`
- If running Python 3.14, prefer `VECTOR_BACKEND=local` (current Chroma builds are more stable on 3.11/3.12).

## Privacy Defaults

- Local DB/filesystem storage by default
- No forced cloud sync
- External integrations opt-in only via env flags
- Docker ports are bound to `127.0.0.1` by default (localhost-only)
- Rotate secrets immediately if they were shared in logs/chat history

## Test

```bash
python3 -m unittest discover -s creator_intelligence_app/tests -p 'test_*.py'
```

## Docker (Optional)

```bash
docker compose up --build
```

Production-like profile:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

See deployment hardening guide:
- [DEPLOY.md](/Users/maestro/LinkedIN analysis/creator_intelligence_app/docs/DEPLOY.md)

## Devcontainer / Codespaces

Open the repo in a devcontainer with:
- [devcontainer.json](</Users/maestro/LinkedIN analysis/.devcontainer/devcontainer.json>)
