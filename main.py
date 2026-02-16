"""
JAF API entry point.

Usage:
    DATABASE_URL=postgresql+asyncpg://user@localhost/jaf_demo \
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os

# Set DATABASE_URL default before any framework imports (which read it at module level)
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://alexzamfir@localhost/jaf_demo"

from jaf.api.main import app  # noqa: F401, E402
