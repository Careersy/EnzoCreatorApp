# TASKLIST: Creator Intelligence Web App

## Stage 1: Planning (Completed)

- [x] Define architecture recommendation
- [x] Define stack decision
- [x] Define data model/schema
- [x] Define ingestion plan
- [x] Define retrieval strategy
- [x] Define style fidelity strategy
- [x] Define privacy model
- [x] Define phased roadmap
- [x] Produce `PLAN.md`
- [x] Produce `ARCHITECTURE.md`
- [x] Produce `TASKLIST.md`

## Stage 2: Build

### Phase 1 MVP (Implement fully)

- [x] Scaffold project structure (`creator_intelligence_app/`)
- [x] Build FastAPI app + health endpoint
- [x] Build local browser UI with required tabs
- [x] Implement DB bootstrap and repositories
- [x] Implement file ingestion (`PDF`, `TXT`, `MD`)
- [x] Implement pasted text ingestion + tagging
- [x] Implement chunking + metadata extraction
- [x] Implement graph loader/query from existing creator graph
- [x] Implement semantic retrieval baseline
- [x] Implement hybrid retrieval orchestration
- [x] Implement user style profile extraction
- [x] Implement anti-generic-AI detector and phrase rules
- [x] Implement blueprint builder (`Use/Prefer/Avoid/Unclear`)
- [x] Implement rewrite engine
- [x] Implement draft generation engine
- [x] Implement expansion engine
- [x] Implement content planner service
- [x] Implement API actions for all core commands
- [x] Implement markdown export
- [x] Add optional Notion sync stub endpoint
- [x] Add setup docs and `.env.example`
- [x] Add optional Docker setup
- [x] Add tests for core services
- [x] Run local validation checks

### Phase 2 (Stub now)

- [x] Add stronger embedding backend
- [x] Add side-by-side diff and scoring UI
- [x] Add saved blueprints and weighting controls
- [x] Add richer style matching and calibration

### Phase 3 (Stub now)

- [x] Add topic map and multi-post series automation
- [x] Add calendar-first planning workflows
- [x] Add repurposing pipelines by platform

### Phase 4 (Stub now)

- [x] Add Notion sync implementation
- [x] Add GitHub export implementation
- [x] Add remote deployment hardening and auth docs
- [x] Add optional API token auth middleware (Bearer / X-API-Key)
- [x] Add configurable CORS and security headers middleware
- [x] Add production compose profile and deployment guide

## Definition of Done for this implementation pass

- [x] Local web app runs on localhost
- [x] User can upload/paste and tag sources
- [x] User can query creator graph
- [x] Rewrite uses retrieval + style profile
- [x] Generate uses retrieval + style profile
- [x] Expand uses retrieval + style profile
- [x] User can export markdown locally
- [x] Core tests pass
