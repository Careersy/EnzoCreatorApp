"""Vercel/FastAPI entrypoint.

This file exists so hosting platforms that auto-detect `main.py`
can import a top-level `app` object directly.
"""

from creator_intelligence_app.app.main import app

