#!/usr/bin/env bash
set -euo pipefail

uvicorn creator_intelligence_app.app.main:app --reload --host ${APP_HOST:-127.0.0.1} --port ${APP_PORT:-8000}
