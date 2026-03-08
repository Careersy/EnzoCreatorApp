"""FastAPI app entrypoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from creator_intelligence_app.app.api.routes import router as api_router
from creator_intelligence_app.app.config.settings import SETTINGS, parse_cors_origins, parse_model_options
from creator_intelligence_app.app.security import is_authorized, should_skip_auth


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(title=SETTINGS.app_name, version="0.1.0")
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(SETTINGS.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if SETTINGS.api_auth_enabled and path.startswith("/api/") and not should_skip_auth(path):
        if not is_authorized(request.headers, SETTINGS.api_auth_token):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    if SETTINGS.secure_headers_enabled:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    default_model = SETTINGS.openai_model
    if str(SETTINGS.llm_provider).lower() == "anthropic":
        default_model = SETTINGS.anthropic_model
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": SETTINGS.app_name,
            "private_mode": SETTINGS.local_private_mode,
            "api_auth_enabled": SETTINGS.api_auth_enabled,
            "default_model": default_model,
            "model_options": parse_model_options(SETTINGS.available_models),
        },
    )
