# Deployment and Hardening Guide

## Security Controls Added

- Optional API token auth (`API_AUTH_ENABLED=true`)
- Supports `Authorization: Bearer <token>` or `X-API-Key`
- Security headers middleware
- Configurable CORS allowlist
- Upload size limit (`MAX_UPLOAD_MB`)
- Non-root Docker runtime user

## Production Environment Variables

Set these in `.env` before remote/self-hosted deployment:

```bash
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
LOCAL_PRIVATE_MODE=true
SECURE_HEADERS_ENABLED=true
API_AUTH_ENABLED=true
API_AUTH_TOKEN=replace-with-long-random-secret
CORS_ALLOW_ORIGINS=https://your-domain.com
MAX_UPLOAD_MB=20
```

Also set integration/model keys only if needed:

- `OPENAI_API_KEY`
- `NOTION_*`
- `GITHUB_*`
- `NEO4J_*`

## Run Production Profile with Docker Compose

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

The compose file is localhost-only by default:
- `127.0.0.1:8000:8000`

Check health:

```bash
curl http://127.0.0.1:8000/api/health
```

## Browser UI in Auth Mode

When `API_AUTH_ENABLED=true`, API calls are protected.

In the app UI:

1. Open `Settings`
2. Paste `API_AUTH_TOKEN` in `API Token (for protected API mode)`
3. Save

The token is stored in browser local storage and attached to API calls.

## Reverse Proxy Recommendation

Terminate TLS at a reverse proxy (Caddy, Nginx, Traefik), then forward to `127.0.0.1:8000`.

Minimum recommendations:

- Force HTTPS
- Restrict allowed origins via `CORS_ALLOW_ORIGINS`
- Keep `API_AUTH_ENABLED=true` for non-local access
- Rotate `API_AUTH_TOKEN` if shared
- Keep `.env` outside public repositories

## Notes for Neo4j Free Tier

- Use `dry_run` imports first
- Keep graph hash skip enabled (default) to avoid unnecessary writes
- Avoid frequent full `clear_existing` imports
