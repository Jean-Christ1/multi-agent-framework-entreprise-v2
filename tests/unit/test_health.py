import importlib
import types

import pytest

from framework.health import check_health


class _ConnOk:
    async def execute(self, _query):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _EngineOk:
    def connect(self):
        return _ConnOk()


class _EngineFail:
    def connect(self):
        raise RuntimeError("db connect failed")


@pytest.mark.asyncio
async def test_check_health_database_ok(monkeypatch):
    fake_db = types.SimpleNamespace(engine=_EngineOk())

    def _fake_import(name: str):
        assert name == "framework.persistence.database"
        return fake_db

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    result = await check_health()
    assert result["status"] == "healthy"
    assert result["database"] == "ok"
    assert "version" in result


@pytest.mark.asyncio
async def test_check_health_database_import_error(monkeypatch):
    def _fake_import(_name: str):
        raise ValueError("DATABASE_URL environment variable is required.")

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    result = await check_health()
    assert result["status"] == "unhealthy"
    assert result["database"] == "error"
    assert "details" in result
    assert "DATABASE_URL" in result["details"]["database"]


@pytest.mark.asyncio
async def test_check_health_database_connect_error(monkeypatch):
    fake_db = types.SimpleNamespace(engine=_EngineFail())

    def _fake_import(name: str):
        assert name == "framework.persistence.database"
        return fake_db

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    result = await check_health()
    assert result["status"] == "unhealthy"
    assert result["database"] == "error"
    assert result["details"]["database"] == "db connect failed"
