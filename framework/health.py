"""
Health check utilities for JAF Framework.
"""

from __future__ import annotations

import importlib
from typing import Any

from sqlalchemy import text

from framework import __version__


async def check_health() -> dict[str, Any]:
    """
    Run framework health checks.

    Returns:
        {
          "status": "healthy" | "unhealthy",
          "database": "ok" | "error",
          "version": "<framework version>",
          # optional when unhealthy:
          "details": {"database": "<error message>"}
        }
    """

    base: dict[str, Any] = {
        "status": "healthy",
        "database": "ok",
        "version": __version__,
    }

    # Import lazily: framework.persistence.database raises on import if DATABASE_URL is missing.
    try:
        db = importlib.import_module("framework.persistence.database")
    except Exception as exc:
        base["status"] = "unhealthy"
        base["database"] = "error"
        base["details"] = {"database": str(exc)}
        return base

    try:
        async with db.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        base["status"] = "unhealthy"
        base["database"] = "error"
        base["details"] = {"database": str(exc)}

    return base
