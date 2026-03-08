"""Optional Notion sync integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from creator_intelligence_app.app.config.settings import SETTINGS


class NotionSyncService:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.api_key = SETTINGS.notion_api_key
        self.database_id = SETTINGS.notion_database_id
        self.parent_page_id = SETTINGS.notion_parent_page_id
        self.base_url = "https://api.notion.com/v1"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def _title_content(self, payload: dict[str, Any]) -> str:
        title = str(payload.get("title") or payload.get("name") or "").strip()
        if title:
            return title
        return f"Creator Draft {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"

    def _create_page_under_parent(self, payload: dict[str, Any]) -> dict[str, Any]:
        body_text = str(payload.get("body") or payload.get("content") or payload.get("summary") or "")
        title = self._title_content(payload)
        request_body = {
            "parent": {"page_id": self.parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title[:2000]},
                        }
                    ]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": (body_text or str(payload))[:2000]},
                            }
                        ]
                    },
                }
            ],
        }

        with httpx.Client(timeout=20.0) as client:
            res = client.post(f"{self.base_url}/pages", headers=self._headers(), json=request_body)
            if res.status_code >= 400:
                return {"synced": False, "status_code": res.status_code, "error": res.text}
            data = res.json()
        return {
            "synced": True,
            "target": "page",
            "page_id": data.get("id"),
            "url": data.get("url"),
        }

    def _create_page_in_database(self, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=20.0) as client:
            db_res = client.get(f"{self.base_url}/databases/{self.database_id}", headers=self._headers())
            if db_res.status_code >= 400:
                return {"synced": False, "status_code": db_res.status_code, "error": db_res.text}
            db_data = db_res.json()
            props = db_data.get("properties", {})
            title_prop = None
            status_prop = None
            rich_text_prop = None
            for name, cfg in props.items():
                p_type = cfg.get("type")
                if p_type == "title" and title_prop is None:
                    title_prop = name
                elif p_type == "status" and status_prop is None:
                    status_prop = name
                elif p_type == "rich_text" and rich_text_prop is None:
                    rich_text_prop = name

            if not title_prop:
                return {"synced": False, "error": "No title property found in target Notion database."}

            notion_properties: dict[str, Any] = {
                title_prop: {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": self._title_content(payload)[:2000]},
                        }
                    ]
                }
            }

            if status_prop and payload.get("status"):
                notion_properties[status_prop] = {"status": {"name": str(payload["status"])[:100]}}

            if rich_text_prop and payload.get("summary"):
                notion_properties[rich_text_prop] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": str(payload["summary"])[:2000]},
                        }
                    ]
                }

            request_body = {"parent": {"database_id": self.database_id}, "properties": notion_properties}
            res = client.post(f"{self.base_url}/pages", headers=self._headers(), json=request_body)
            if res.status_code >= 400:
                return {"synced": False, "status_code": res.status_code, "error": res.text}
            data = res.json()
        return {
            "synced": True,
            "target": "database",
            "database_id": self.database_id,
            "page_id": data.get("id"),
            "url": data.get("url"),
        }

    def sync_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {
                "synced": False,
                "reason": "Notion integration disabled. Enable NOTION_ENABLED=true to activate.",
            }

        if not self.api_key:
            return {"synced": False, "reason": "NOTION_API_KEY is missing."}

        if self.database_id:
            return self._create_page_in_database(payload)
        if self.parent_page_id:
            return self._create_page_under_parent(payload)
        return {
            "synced": False,
            "reason": "Set NOTION_DATABASE_ID or NOTION_PARENT_PAGE_ID to enable syncing.",
        }
