"""Bootstrap utilities for application services."""

from __future__ import annotations

from creator_intelligence_app.app.config.settings import DEFAULT_GRAPH_PATH, DB_PATH, SETTINGS, ensure_data_dirs
from creator_intelligence_app.app.db.database import Database, init_db
from creator_intelligence_app.app.services.content_service import ContentIntelligenceService
from creator_intelligence_app.graph.graph_client import GraphClient
from creator_intelligence_app.integrations.github_export import GitHubExportService
from creator_intelligence_app.integrations.notion_sync import NotionSyncService


class ServiceContainer:
    def __init__(self) -> None:
        ensure_data_dirs()
        init_db(DB_PATH)

        db = Database(DB_PATH)
        graph_client = GraphClient(db=db, graph_json_path=DEFAULT_GRAPH_PATH)
        notion = NotionSyncService(enabled=SETTINGS.notion_enabled)
        github = GitHubExportService(enabled=SETTINGS.github_export_enabled)

        self.content_service = ContentIntelligenceService(
            db=db,
            graph_client=graph_client,
            notion_service=notion,
            github_service=github,
        )

        self.content_service.load_creator_graph()


container = ServiceContainer()
