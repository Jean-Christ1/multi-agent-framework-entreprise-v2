"""
Pytest configuration for shared fixtures.

- Async tests handled by pytest-asyncio (no custom event_loop)
- DATABASE_URL loaded from .env
- Provides an AsyncSession for integration tests
"""

import os
from dotenv import load_dotenv

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager

# Load environment variables from .env
load_dotenv(dotenv_path=".env", override=True)


@pytest_asyncio.fixture
async def async_session():
    """
    Async SQLAlchemy session fixture for integration tests.

    - Uses DATABASE_URL from environment
    - Creates a fresh AsyncSession per test
    - Properly disposes engine after use
    - Also provides the async_engine as session.bind for creating session_makers
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in environment")

    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )

    SessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async with SessionLocal() as session:
        # Attach the async engine to the session for tests to use
        session.async_engine = engine
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def session_maker():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in environment")

    engine = create_async_engine(database_url, echo=False, future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _maker():
        async with SessionLocal() as session:
            yield session

    yield _maker

    await engine.dispose()
