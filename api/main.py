"""
api/main.py

FastAPI entry point for ADOS — the Architectural Document Operating System.

Responsibility boundary:
    This module does application-level wiring only:
        • FastAPI app + OpenAPI metadata
        • CORS and request-logging middleware
        • Router registration under their real prefixes
        • A couple of infrastructure endpoints (/health, /)

    Business logic does NOT live here — it lives in brand/ and is exposed
    through api/routers/.

    ADOS was split out of a larger monorepo (REVELATION + construmind lived
    alongside it there) into its own repository; this file only mounts the
    eight ADOS routers. No render pipeline, auth stack, or database — ADOS's
    own persistence is the file-backed stores under brand/store and
    brand/project, which need no external service to run.

Configuration env variables (all optional, with fallbacks):
    ALLOWED_ORIGINS   Comma-separated CORS origin list.
                      Default: http://localhost:3100,http://127.0.0.1:3100
                      (ados-web's own dev port — see ados-web/README.md)
                      plus :3000/:5173 for other local frontends.
    LOG_LEVEL         Python logging level name. Default: INFO

Run (development):
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import time

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.routers import ados_project as ados_project_router
from api.routers import brand as brand_router
from api.routers import closed_loop as closed_loop_router
from api.routers import command as command_router
from api.routers import content_intelligence as content_intelligence_router
from api.routers import design_intent as design_intent_router
from api.routers import narrative as narrative_router
from api.routers import semantic_intent as semantic_intent_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _env_origins() -> list[str]:
    # ados-web (the real ADOS frontend, per its own README-documented dev
    # port) runs on :3100. :3000/:5173 are kept for other local frontends
    # that may talk to the same API during development.
    raw = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,"
        "http://localhost:3100,http://127.0.0.1:3100",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

_IS_PROD = os.environ.get("ENVIRONMENT", "development").lower() == "production"

app = FastAPI(
    title="ADOS — Architectural Document Operating System",
    description=(
        "REST API for the ADOS Brand and Document system: brand identity, "
        "content modelling, narrative and design-intent generation, "
        "command compilation, and the closed-loop iteration engine."
    ),
    version="1.0.0",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=_env_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    """Logs every request with method, path, status and duration.

    Does not log the request body (payloads may carry client content).
    """
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"

    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
app.include_router(semantic_intent_router.router, prefix="/api/v2", tags=["semantic-intent"])
app.include_router(content_intelligence_router.router, prefix="/api/v2/ados-projects", tags=["content-intelligence"])
app.include_router(narrative_router.router, prefix="/api/v2/ados-projects", tags=["narrative"])
app.include_router(design_intent_router.router, prefix="/api/v2/ados-projects", tags=["design-intent"])
app.include_router(command_router.router, prefix="/api/v2/ados-projects", tags=["command-generation"])
app.include_router(closed_loop_router.router, prefix="/api/v2/ados-projects", tags=["closed-loop"])


# ---------------------------------------------------------------------------
# Infrastructure endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Infrastructure"])
async def health_check() -> dict:
    """Liveness check. ADOS has no external services to report on —
    if this responds, the file-backed stores it depends on are reachable
    (they are just paths on local disk)."""
    return {"status": "ok"}


@app.get("/", tags=["Infrastructure"])
async def root() -> dict:
    """API root — version and documentation links."""
    return {
        "name": "ADOS — Architectural Document Operating System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=_LOG_LEVEL.lower(),
    )
