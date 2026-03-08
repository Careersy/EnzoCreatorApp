"""Security helpers and middleware utilities."""

from __future__ import annotations

import hmac
from typing import Mapping


def extract_api_token(headers: Mapping[str, str]) -> str:
    auth = str(headers.get("authorization", "")).strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return str(headers.get("x-api-key", "")).strip()


def is_authorized(headers: Mapping[str, str], expected_token: str | None) -> bool:
    if not expected_token:
        return False
    supplied = extract_api_token(headers)
    if not supplied:
        return False
    return hmac.compare_digest(supplied, expected_token)


def should_skip_auth(path: str) -> bool:
    return path in {"/", "/api/health"} or path.startswith("/static/")
