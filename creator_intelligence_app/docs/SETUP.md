# Setup Guide

## Prerequisites

- Python 3.11+
- `knowledge-graph.json` present at repo root (or set `CREATOR_GRAPH_PATH`)

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn creator_intelligence_app.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open: `http://127.0.0.1:8000`

## Optional Integrations

Set only what you need in `.env`:

- Notion:
  - `NOTION_ENABLED=true`
  - `NOTION_API_KEY=...`
  - `NOTION_DATABASE_ID=...` (recommended) or `NOTION_PARENT_PAGE_ID=...`
- GitHub export:
  - `GITHUB_EXPORT_ENABLED=true`
  - `GITHUB_TOKEN=...`
  - `GITHUB_OWNER=...`
  - `GITHUB_REPO=...`
  - optional `GITHUB_BRANCH`, `GITHUB_PATH_PREFIX`

## Model Connection

Set in `.env`:

- `LLM_PROVIDER=auto` (`openai` or `anthropic` also supported)
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-4o-mini` (or your preferred OpenAI model)
- `ANTHROPIC_API_KEY=...`
- `ANTHROPIC_MODEL=claude-3-5-sonnet-latest`
- optional `AVAILABLE_MODELS=gpt-4o-mini,gpt-4.1-mini,gpt-4.1,claude-3-5-sonnet-latest,claude-3-7-sonnet-latest`
- optional `OPENAI_BASE_URL=` (only if using an OpenAI-compatible gateway)
- optional `VECTOR_BACKEND=local|chroma` and `CHROMA_PERSIST_DIR=...`

Note: if you run Python 3.14, Chroma can fail due upstream compatibility. Use `VECTOR_BACKEND=local` or run with Python 3.11/3.12 for Chroma.

Then restart the app and in `Settings` use **Check model connection** (`GET /api/model/status`).

## Security and Hardening Options

Set in `.env` as needed:

- `API_AUTH_ENABLED=true`
- `API_AUTH_TOKEN=<long-random-secret>`
- `CORS_ALLOW_ORIGINS=http://127.0.0.1:8000,http://localhost:8000`
- `SECURE_HEADERS_ENABLED=true`
- `MAX_UPLOAD_MB=20`

If API auth is enabled, open `Settings` in the web app and save the API token in `API Token (for protected API mode)` for browser API calls.

## Ingestion Notes

- File ingestion supports background jobs (UI default for uploaded files)
- Poll job status via `GET /api/jobs/{job_id}`
- Content dedupe is hash-based; use `allow_duplicate=true` to override
- Rebuild retrieval chunks with `POST /api/reindex`

## Quick Validation

```bash
python3 -m unittest discover -s creator_intelligence_app/tests -p 'test_*.py'
```

## Data Paths

- SQLite DB: `creator_intelligence_app/data/app.db`
- uploads: `creator_intelligence_app/data/uploads`
- exports: `creator_intelligence_app/data/exports`

## Privacy Defaults

- local-only by default
- no cloud sync required
- integrations are explicit opt-in
- rotate credentials immediately if they were shared publicly

## Optional Docker

```bash
docker compose up --build
```

Production-like compose profile:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Optional Devcontainer

Use `.devcontainer/devcontainer.json` for Codespaces/devcontainer setup.

## Deployment Guide

See `creator_intelligence_app/docs/DEPLOY.md` for remote/self-hosted hardening.
