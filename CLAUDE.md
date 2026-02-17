# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

**JAF (Jems Agent Framework)** -- A hybrid neuro-symbolic automation framework based on the Actor Model.
Author: Armand Amoussou. Repository hosted on GitLab at `gitlab.com/llm-ai-agents-agentic-ai/multi-agent-framework-entreprise-v2`.
License: Proprietary. Python 3.11+. Package name: `jaf-framework`. Current version: `0.1.0`.

## Governance Rules

- Armand Amoussou is the sole author and decision-maker. Claude AI is a technical assistance tool only.
- No emojis. No informal tone. No approximations. No pseudo-code unless explicitly requested.
- No use of Poetry (pip + venv only). No undeclared dependencies.
- Every deliverable must be deterministic, traceable, reproducible, testable, documented.
- Reason as if the project is under external audit, subject to production incidents, and carries human liability.

## Language Directive -- Strict English Only

All output produced for this repository must be written exclusively in English. No other language is permitted in any deliverable.

Mandatory requirements:
- Enterprise-grade professional English.
- Precise technical English with rigorous architectural terminology.
- Formal, institutional, structured tone appropriate for enterprise software architecture documentation.
- Flawless syntax and grammar. No clumsy literal translations. No francophone syntactic influence. No language mixing. No French words or expressions.
- Titles, sections, comments, descriptions, technical justifications, analyses, recommendations, and guides must be entirely in English.
- Code comments in generated or modified code must use English exclusively.
- Professional English for documentation and communication.

## Build, Lint, and Test Commands

```bash
# Install (tiered)
pip install -r requirements-core.txt    # Core only (no LLM, no cmake)
pip install -r requirements-llm.txt     # Core + LLM (CrewAI, OpenAI)
pip install -r requirements.txt         # Full (core + LLM + FastAPI + httpx)
pip install -r requirements-demo.txt    # ETL demo extras (pyarrow, pandas, faker)

# Install in editable mode (dev)
pip install -e .[dev]

# Lint
ruff check .
black --check --diff .
mypy framework/

# Format
black .
ruff check --fix .

# Pre-commit hooks
pre-commit install
pre-commit run --all-files

# Tests
pytest                                          # Run all tests
pytest --cov=framework --cov-report=html        # With coverage
pytest tests/unit/test_actors.py -v             # Single test file
pytest tests/unit/test_orchestrator.py -k "test_name" -v  # Single test

# Build package
python -m build

# CLI
jaf new my_project      # Scaffold new project
jaf --version           # Show version

# API server
uvicorn jaf.api.main:app --reload --host 0.0.0.0 --port 8000

# ETL demo
python -m examples.etl_demo.run_demo --standalone
```

## Database Setup

PostgreSQL is required for persistence. Migration files are in `migrations/`:
```bash
createdb jaf_dev
psql jaf_dev < migrations/001_create_processes.sql
psql jaf_dev < migrations/002_create_llm_telemetry.sql
psql jaf_dev < migrations/003_create_process_events.sql
```
For tests without PostgreSQL, set `DATABASE_URL=sqlite+aiosqlite:///./test.db`.

## Architecture Overview

JAF implements a three-layer architecture with three execution modes:

### Three Execution Modes

| Mode            | Engine          | LLM Required | Cost    |
|-----------------|-----------------|--------------|---------|
| **Traditional** | NativeEngine    | No           | $0.00   |
| **Agentic**     | CrewAIAdapter   | Yes          | ~$0.05  |
| **Multi-Agent** | CrewAIAdapter   | Yes          | ~$0.12  |

### Three Layers

1. **Engine Layer (Brain)**: `EngineAbstraction` ABC with plan-execute-evaluate loop.
   - `NativeEngine` -- deterministic, no LLM, uses pre-built or sequential plans.
   - `CrewAIAdapter` -- LLM-powered planning and execution via CrewAI agents.
   - `VertexAIAdapter` -- Vertex AI compatibility adapter.
   - `EngineFactory` -- auto-selects engine based on actor `llm_config` (all `None` = NativeEngine, any set = CrewAIAdapter). Override with `engine_type="native"|"crewai"|"vertexai"`.

2. **Adapter Layer (Muscle)**: Pluggable execution backends (CrewAI, Native, LangGraph planned).

3. **Actor Layer**: Business logic units implementing `Actor` ABC via `configure()`. Each actor declares `name`, `description`, `goal`, `tools` (list of callables), and optional `llm_config` (None = deterministic).

### Key Components

- **ActorRegistry**: Singleton. `register(name, class)`, `get(name)`, `list()`, `clear()`.
- **Orchestrator**: Coordinates Engine + Actors + EventBus + Persistence. Runs the full lifecycle (PENDING -> RUNNING -> COMPLETED/FAILED). Supports resume, dry-run validation, step timeouts, retry with exponential backoff.
- **ProcessStateMachine**: Enforces valid state transitions. Terminal states: COMPLETED, FAILED.
- **EventBus**: In-process pub/sub singleton (`get_event_bus()`). Broadcasts `AgentAction` events. Thread-safe.
- **Persistence**: PostgreSQL + async SQLAlchemy. `ProcessRepository` for CRUD on `processes` table (JSONB for plan/context). `llm_telemetry` table tracks token usage/costs. `process_events` table for audit trail.
- **Data Contracts**: `DataContract` (Pydantic base), `@tool_contract` decorator, `SchemaRegistry` for OpenAPI export.
- **TypedContext**: Type-safe context passing between actors.
- **Observability**: `TelemetryCalculator`, `TokenUsage`, structured logging via `framework.logging`.

### Two Package Trees

There are two distinct package trees in the codebase:

1. **`framework/`** -- The core JAF library (packaged as `jaf-framework` wheel). This is the public API. Import from here: `from framework import Actor, Orchestrator, ...`
2. **`jaf/`** -- A higher-level application layer with FastAPI API (`jaf/api/`), static SPA UI (`jaf/static/`), demo actors (`jaf/demos/`), and alternative core models (`jaf/core/`). This is the API server and CEO demo application. It re-implements some core abstractions with its own `Actor`, `ActorRegistry`, `Tool` decorator, and `EngineAbstraction`.

The `agents/` directory contains business-domain actors (ProvisioningActor, AnnuaireActor, HabilitationActor, PiramidActor, GEAIActor, CEOAgent) plus an `orchestrator/` sub-package with planning, tools, and scenario classification.

## Data Models (framework/types.py)

All Pydantic v2 models: `LLMConfig`, `Plan`, `PlanStep`, `StepResult`, `PlanUpdate`, `AgentAction`.
Plan statuses: `PLANNING | EXECUTING | COMPLETED | FAILED`.
PlanUpdate actions: `continue | modify | retry | abort`.

## Environment Variables

Key variables (see `env.example`):
- `DATABASE_URL` -- PostgreSQL async connection string (required for persistence)
- `OPENAI_API_KEY` -- Required for LLM operations
- `DEFAULT_ENGINE` -- `crewai` or `native`
- `DEFAULT_MODEL` -- e.g. `gpt-4o-mini`
- `ENABLE_PERSISTENCE`, `ENABLE_EVENTS`, `ENABLE_METRICS` -- feature flags

## CI/CD (GitLab)

Pipeline stages: lint (ruff, black) -> test (pytest + coverage) -> build (python -m build) -> deploy (mkdocs pages + PyPI publish on tag `v*`).
Publish triggers on tags matching `^v\d+\.\d+\.\d+$`.

## Git Branching & Versioning

- Branches follow `feature/JAF-XX`, `fix/`, `Tests/JAF-XX` pattern. ~50 remote branches exist.
- Tags: v1.0.0 through v1.4.2 (30 tags total). All currently point to the same initial commit.
- Version is defined in two places that must stay in sync: `framework/_version.py` and `pyproject.toml [project] version`.
- MRs are submitted against `main` branch.

## Test Configuration

Pytest config is in `pyproject.toml`. Several test files are explicitly ignored via `addopts --ignore=` (deprecated tests and DB-dependent integration tests). Active unit tests are in `tests/unit/`. Integration tests in `tests/integration/` mostly require a live PostgreSQL database.

## Tool Tooling

- Black (line-length 88, target py311)
- Ruff (extends-exclude deprecated test files)
- Mypy (excludes tests/, examples/, migrations/, agents/)
- Pre-commit hooks: black, ruff, mypy, trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-added-large-files (max 1000KB), check-merge-conflict, mixed-line-ending (LF)

## API Endpoints (jaf/api/)

- `GET /` -- Serves SPA index.html
- `GET /health` -- Health check
- `GET /api/v1/processes` -- List processes (optional `?status=` filter)
- `GET /api/v1/processes/{id}` -- Get process with plan
- `GET /api/v1/processes/{id}/events` -- Process event audit trail
- Demo routes via `jaf/api/routes/demos.py`
- SSE stream via `jaf/api/routes/stream.py`
