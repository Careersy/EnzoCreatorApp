"""Application settings and path configuration."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv(Path.cwd() / ".env")


ROOT_DIR = Path(__file__).resolve().parents[2]


def _resolve_data_dir() -> Path:
    configured = os.getenv("APP_DATA_DIR")
    if configured:
        return Path(configured).expanduser()

    default = ROOT_DIR / "data"
    running_on_vercel = os.getenv("VERCEL") == "1"
    if running_on_vercel:
        return Path(tempfile.gettempdir()) / "enzo_creator_app_data"

    try:
        default.mkdir(parents=True, exist_ok=True)
        probe = default / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return default
    except Exception:
        return Path(tempfile.gettempdir()) / "enzo_creator_app_data"


DATA_DIR = _resolve_data_dir()
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
INDEX_DIR = DATA_DIR / "indexes"
DB_PATH = DATA_DIR / "app.db"
DEFAULT_GRAPH_PATH = Path(os.getenv("CREATOR_GRAPH_PATH", str(Path.cwd() / "knowledge-graph.json")))


@dataclass(slots=True)
class Settings:
    app_name: str = "Enzo Creator App"
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("APP_PORT", "8000"))
    app_env: str = os.getenv("APP_ENV", "development")
    cors_allow_origins: str = os.getenv("CORS_ALLOW_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    secure_headers_enabled: bool = os.getenv("SECURE_HEADERS_ENABLED", "true").lower() == "true"
    api_auth_enabled: bool = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
    api_auth_token: str | None = os.getenv("API_AUTH_TOKEN")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    available_models: str = os.getenv(
        "AVAILABLE_MODELS",
        "claude-sonnet-4-6,claude-opus-4-6,claude-haiku-4-5-20251001,claude-sonnet-4-5-20250929,gpt-4o-mini,gpt-4.1-mini,gpt-4.1",
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    vector_backend: str = os.getenv("VECTOR_BACKEND", "local")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", str(INDEX_DIR / "chroma"))
    local_private_mode: bool = os.getenv("LOCAL_PRIVATE_MODE", "true").lower() == "true"
    notion_enabled: bool = os.getenv("NOTION_ENABLED", "false").lower() == "true"
    notion_api_key: str | None = os.getenv("NOTION_API_KEY")
    notion_database_id: str | None = os.getenv("NOTION_DATABASE_ID")
    notion_parent_page_id: str | None = os.getenv("NOTION_PARENT_PAGE_ID")
    github_export_enabled: bool = os.getenv("GITHUB_EXPORT_ENABLED", "false").lower() == "true"
    github_token: str | None = os.getenv("GITHUB_TOKEN")
    github_owner: str | None = os.getenv("GITHUB_OWNER")
    github_repo: str | None = os.getenv("GITHUB_REPO")
    github_branch: str = os.getenv("GITHUB_BRANCH", "main")
    github_path_prefix: str = os.getenv("GITHUB_PATH_PREFIX", "")
    neo4j_uri: str | None = os.getenv("NEO4J_URI")
    neo4j_username: str | None = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER")
    neo4j_password: str | None = os.getenv("NEO4J_PASSWORD")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    neo4j_enabled: bool = bool(
        os.getenv("NEO4J_URI") and (os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER")) and os.getenv("NEO4J_PASSWORD")
    )


SETTINGS = Settings()


def ensure_data_dirs() -> None:
    for path in (DATA_DIR, UPLOAD_DIR, EXPORT_DIR, INDEX_DIR):
        path.mkdir(parents=True, exist_ok=True)


def parse_cors_origins(raw: str) -> list[str]:
    origins = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    return origins or ["http://127.0.0.1:8000", "http://localhost:8000"]


def parse_model_options(raw: str) -> list[str]:
    models = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    return models or [
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20250929",
        "gpt-4o-mini",
        "gpt-4.1-mini",
        "gpt-4.1",
    ]
