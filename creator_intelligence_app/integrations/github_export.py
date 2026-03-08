"""Optional GitHub export integration."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from creator_intelligence_app.app.config.settings import SETTINGS


class GitHubExportService:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.token = SETTINGS.github_token
        self.owner = SETTINGS.github_owner
        self.repo = SETTINGS.github_repo
        self.branch = SETTINGS.github_branch
        self.path_prefix = SETTINGS.github_path_prefix.strip("/")
        self.base_url = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _full_path(self, relative_path: str) -> str:
        clean = relative_path.strip("/")
        if self.path_prefix:
            return f"{self.path_prefix}/{clean}".strip("/")
        return clean

    def export(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {
                "exported": False,
                "reason": "GitHub export disabled. Enable GITHUB_EXPORT_ENABLED=true to activate.",
            }

        if not (self.token and self.owner and self.repo):
            return {
                "exported": False,
                "reason": "Missing GitHub configuration. Set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO.",
            }

        file_path = self._full_path(str(payload.get("file_path", "exports/draft.md")))
        content = str(payload.get("content", ""))
        message = str(payload.get("message", f"Update {file_path}"))
        branch = str(payload.get("branch", self.branch))

        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{file_path}"

        with httpx.Client(timeout=20.0) as client:
            existing_sha = None
            get_res = client.get(url, headers=self._headers(), params={"ref": branch})
            if get_res.status_code == 200:
                existing_sha = get_res.json().get("sha")
            elif get_res.status_code not in (404,):
                return {"exported": False, "status_code": get_res.status_code, "error": get_res.text}

            body: dict[str, Any] = {
                "message": message,
                "content": encoded,
                "branch": branch,
            }
            if existing_sha:
                body["sha"] = existing_sha

            put_res = client.put(url, headers=self._headers(), json=body)
            if put_res.status_code >= 400:
                return {"exported": False, "status_code": put_res.status_code, "error": put_res.text}
            data = put_res.json()

        return {
            "exported": True,
            "repo": f"{self.owner}/{self.repo}",
            "path": file_path,
            "branch": branch,
            "commit_sha": (data.get("commit") or {}).get("sha"),
            "content_url": (data.get("content") or {}).get("html_url"),
        }
