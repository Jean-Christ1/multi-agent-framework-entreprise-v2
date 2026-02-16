"""
JAF API — FastAPI Application
==============================

Serves the CEO demo UI and API endpoints.

Usage:
    uvicorn jaf.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from jaf.api.routes.demos import router as demos_router
from jaf.api.routes.stream import router as stream_router
from jaf.api.routes.processes import router as processes_router

logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────

app = FastAPI(
    title="JAF - Jems AI Framework",
    description="Enterprise-grade Actor-based orchestration framework for AI and traditional automation",
    version="0.1.0",
)

# CORS (allow all for demo purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────

app.include_router(demos_router)
app.include_router(stream_router)
app.include_router(processes_router)

# ── Static files ─────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent.parent / "static"


@app.get("/")
async def serve_index():
    """Serve the main SPA at root."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "JAF API is running. Static files not found at /jaf/static/"}


# Mount static files (CSS, JS, images)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")


# ── Health check ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "framework": "JAF", "version": "0.1.0"}
