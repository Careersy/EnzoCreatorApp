from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from creator_intelligence_app.app.config.settings import SETTINGS
from creator_intelligence_app.app.main import app
from creator_intelligence_app.app.security import extract_api_token, is_authorized


class SecurityHelpersTest(unittest.TestCase):
    def test_extract_api_token(self) -> None:
        self.assertEqual(extract_api_token({"authorization": "Bearer abc"}), "abc")
        self.assertEqual(extract_api_token({"x-api-key": "xyz"}), "xyz")
        self.assertEqual(extract_api_token({}), "")

    def test_is_authorized(self) -> None:
        self.assertTrue(is_authorized({"authorization": "Bearer abc"}, "abc"))
        self.assertTrue(is_authorized({"x-api-key": "abc"}, "abc"))
        self.assertFalse(is_authorized({"authorization": "Bearer bad"}, "abc"))
        self.assertFalse(is_authorized({}, "abc"))
        self.assertFalse(is_authorized({"authorization": "Bearer abc"}, None))


class AuthMiddlewareTest(unittest.TestCase):
    def setUp(self) -> None:
        self.prev_enabled = SETTINGS.api_auth_enabled
        self.prev_token = SETTINGS.api_auth_token
        SETTINGS.api_auth_enabled = True
        SETTINGS.api_auth_token = "test-token"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        SETTINGS.api_auth_enabled = self.prev_enabled
        SETTINGS.api_auth_token = self.prev_token

    def test_auth_required_for_protected_api(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)

        blocked = self.client.get("/api/sources")
        self.assertEqual(blocked.status_code, 401)

        allowed = self.client.get("/api/sources", headers={"Authorization": "Bearer test-token"})
        self.assertEqual(allowed.status_code, 200)

        allowed_alt = self.client.get("/api/sources", headers={"X-API-Key": "test-token"})
        self.assertEqual(allowed_alt.status_code, 200)


if __name__ == "__main__":
    unittest.main()
