"""
Database connection management for JAF framework.

Ticket: JAF-23, JAF-24
"""

import os
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Example: postgresql+asyncpg://user:pass@localhost/jaf_dev"
    )

# Allow sqlite for testing environments, require postgresql for production
if not (
    DATABASE_URL.startswith("postgresql+asyncpg://")
    or DATABASE_URL.startswith("sqlite+aiosqlite://")
):
    raise ValueError(
        "DATABASE_URL must use postgresql+asyncpg:// or sqlite+aiosqlite:// driver"
    )

# Use NullPool only for tests to avoid connection issues with test isolation
# In production, use the default QueuePool for better performance
is_testing = os.getenv("TESTING", "false").lower() == "true"

engine_kwargs: dict[str, Any] = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    "future": True,
}

if is_testing:
    engine_kwargs["poolclass"] = NullPool
else:
    # Production settings with connection pooling
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

async_session_maker = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)  # type: ignore[call-overload]


async def get_session() -> AsyncGenerator[AsyncSession, None]:  # type: ignore[misc]
    """FastAPI dependency for request-scoped sessions."""
    async with async_session_maker() as session:
        yield session


async def create_session() -> AsyncSession:
    """Helper for manual usage in scripts/tests."""
    return async_session_maker()
