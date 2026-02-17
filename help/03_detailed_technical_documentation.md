# 03 -- Detailed Technical Documentation

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, commit 9cbda91

---

## 1. Directory Structure

```
jaf-framework/
├── framework/                     # Core library (packaged as wheel)
│   ├── __init__.py               # Public API exports (31 symbols)
│   ├── _version.py               # Version: 0.1.0
│   ├── types.py                  # Pydantic models (LLMConfig, Plan, PlanStep, etc.)
│   ├── event_bus.py              # EventBus singleton (pub/sub)
│   ├── orchestrator.py           # Orchestrator coordinator (892 lines)
│   ├── state_machine.py          # ProcessStateMachine
│   ├── exceptions.py             # FrameworkException hierarchy
│   ├── health.py                 # Database health probe
│   ├── logging.py                # Structured JSON logging with ContextVar
│   ├── compat.py                 # require_version() utility
│   ├── deprecation.py            # @deprecated decorator
│   ├── actor/
│   │   ├── base_actor.py         # Actor ABC
│   │   └── registry.py           # ActorRegistry singleton (267 lines)
│   ├── engine/
│   │   ├── engine_abstraction.py # EngineAbstraction ABC
│   │   ├── crewai_adapter.py     # CrewAI engine (850+ lines)
│   │   ├── native_engine.py      # Deterministic engine (570 lines)
│   │   ├── vertexai_adapter.py   # Vertex AI adapter (deprecated, 239 lines)
│   │   └── factory.py            # EngineFactory static factory
│   ├── persistence/
│   │   ├── database.py           # Async SQLAlchemy engine setup
│   │   ├── models.py             # ORM models (Process, ProcessEvent)
│   │   ├── schemas.py            # Pydantic serialization schemas
│   │   ├── process_repo.py       # ProcessRepository CRUD
│   │   ├── event_bus_subscriber.py  # DB event persistence
│   │   └── llm_telemetry_repo.py # LLM usage tracking repository
│   ├── data/
│   │   ├── contracts.py          # DataContract, DataEnvelope
│   │   ├── context.py            # TypedContext (MutableMapping)
│   │   ├── validation.py         # DataValidationError
│   │   ├── lineage.py            # Optional data provenance tracking
│   │   └── schema_registry.py    # SchemaRegistry (OpenAPI export)
│   ├── tools/
│   │   └── contracts.py          # ToolContract, @tool_contract decorator
│   ├── observability/
│   │   └── telemetry.py          # TokenUsage, TelemetryCalculator
│   └── cli/
│       ├── main.py               # Typer CLI entry point
│       └── scaffolder.py         # Project scaffolding logic
├── jaf/                           # Application layer
│   ├── __init__.py               # Exports: ProcessState, Actor, Tool, etc.
│   ├── core/
│   │   ├── actor.py              # Alternative Actor ABC with Tool decorator
│   │   ├── engine.py             # Re-export of EngineAbstraction
│   │   └── models.py             # ProcessState, ExecutionMode, NextAction
│   ├── adapters/
│   │   └── native_adapter.py     # OpenAI Responses API engine (1,050 lines)
│   ├── api/
│   │   ├── main.py               # FastAPI app (CORS, routers, static files)
│   │   └── routes/
│   │       ├── demos.py          # POST /api/v1/demos/{id}/run
│   │       ├── stream.py         # GET /api/v1/stream/{process_id} (SSE)
│   │       └── processes.py      # GET /api/v1/processes (audit trail)
│   ├── demos/
│   │   ├── actors.py             # 3 demo actors (Customer, Sales, Provisioning)
│   │   ├── data.py               # Mock business datasets
│   │   └── registry.py           # 8 demo scenarios + runner functions (1,800 lines)
│   ├── events/
│   │   └── __init__.py           # Re-exports from framework.event_bus
│   └── static/
│       ├── index.html            # SPA shell with navigation
│       ├── css/style.css         # Dark-mode design system
│       └── js/
│           ├── app.js            # SPA router + page renderers (650 lines)
│           └── demos.js          # Demo runner + SSE client (400 lines)
├── agents/                        # Business domain actors
│   ├── provisionning_agent.py    # Equipment provisioning (HTTP APIs)
│   ├── annuaire_agent.py         # SOAP directory service
│   ├── habilitation_agent.py     # Permission management (REFSAM)
│   ├── piramid_agent.py          # Building/identity reference data
│   ├── geai_agent.py             # Identity management
│   ├── ceo_agent.py              # Email/communication service
│   └── orchestrator/             # Agent-level orchestration
│       ├── orchestrator_agent.py # Main CrewAI orchestrator (1,211 lines)
│       ├── llm_manager.py        # Quota management + model fallback
│       ├── models.py             # AskRequest/AskResponse schemas
│       ├── session.py            # Trace ID context management
│       ├── scenario_classifier.py # Keyword-based scenario detection
│       ├── utils.py              # Tool creation + sanitization (531 lines)
│       ├── planning/             # Pluggable planner system
│       │   ├── base.py           # Planner protocol
│       │   ├── crewai_adapter.py # CrewAI planner
│       │   ├── deterministic_runner.py # Legacy flow wrapper
│       │   ├── policy.py         # Execution policy
│       │   ├── registry.py       # PlannerRegistry
│       │   └── types.py          # OrchestrationIntent, PlanGraph
│       └── tools/
│           ├── discovery_tool.py # Agent capability discovery
│           └── evaluation_tool.py # System health evaluation
├── examples/                      # Runnable examples
├── tests/                         # Test suite
│   ├── unit/                     # 17 unit test files
│   ├── integration/              # 7 integration test files
│   ├── persistence/              # 2 persistence test files
│   ├── fixtures/                 # Test data (YAML, Parquet)
│   └── mocks/                    # Mock objects
├── migrations/                    # SQL migrations (3 files)
├── docs/                          # Documentation (18 files)
├── pyproject.toml                # Build config, tool config
├── requirements*.txt             # Dependency tiers (4 files)
├── Dockerfile                    # Container definition
├── docker-compose.dev.yml        # Development compose
├── .gitlab-ci.yml                # CI/CD pipeline
├── .pre-commit-config.yaml       # Pre-commit hooks
├── env.example                   # Environment template
├── main.py                       # API entry point
└── CLAUDE.md                     # AI assistant guidance
```

---

## 2. Principal Modules

### 2.1 framework/types.py -- Data Models

All Pydantic v2 models shared across the framework:

| Model | Fields | Purpose |
|-------|--------|---------|
| `LLMConfig` | model, temperature, max_tokens | LLM connection parameters |
| `PlanStep` | id, actor_name, tool_name, parameters, status, parallel_group | Single execution step |
| `Plan` | steps, status (PLANNING/EXECUTING/COMPLETED/FAILED) | Execution plan |
| `StepResult` | output, status (success/error), error | Step execution outcome |
| `PlanUpdate` | action (continue/modify/retry/abort), modified_plan, reason | Engine decision |
| `AgentAction` | agentId, actionType, message, status, timestamp | Event payload |

### 2.2 framework/orchestrator.py -- Execution Coordinator

The Orchestrator manages the full process lifecycle:

**Constructor parameters**:
- `engine: EngineAbstraction` -- execution engine
- `session_maker` -- async SQLAlchemy session factory
- `step_timeout: int = 60` -- per-step timeout in seconds
- `max_retries: int = 3` -- retry count for retryable exceptions
- `retry_delay: float = 5.0` -- base delay for exponential backoff
- `retry_on: tuple = (ConnectionError, TimeoutError)` -- retryable exception types

**Key methods**:
- `run(goal, actors, context, dry_run)` -- main execution entry point
- `resume(process_id)` -- resume an interrupted process
- `_execute_step()` -- step execution with timeout and retry
- `_validate_plan()` -- dry-run plan validation

**Lifecycle**: PENDING -> RUNNING -> (step execution loop) -> COMPLETED or FAILED

### 2.3 framework/engine/ -- Execution Engines

| Engine | LLM | Planning | Execution |
|--------|-----|----------|-----------|
| NativeEngine | No | Pre-built plan or sequential from actor tools | Direct tool invocation |
| CrewAIAdapter | Yes | LLM-generated JSON plan with fallback | CrewAI Agent/Task/Crew |
| VertexAIAdapter | Yes | LLM-based (deprecated) | Synchronous (non-compliant) |

**EngineFactory auto-detection logic**:
- All actors have `llm_config=None` -> NativeEngine
- Any actor has `llm_config` set -> CrewAIAdapter
- Override via `engine_type` parameter: `"native"`, `"crewai"`, `"vertexai"`

---

## 3. Internal and External APIs

### 3.1 Framework Public API (framework/__init__.py)

31 exported symbols organized into 9 categories:

```python
# Version
__version__, __version_info__

# Types
LLMConfig, Plan, PlanStep, PlanUpdate, StepResult, AgentAction

# Actor
Actor, ActorRegistry

# Engine
EngineAbstraction, NativeEngine, CrewAIAdapter, EngineFactory

# Orchestration
Orchestrator, ProcessStateMachine

# Events
EventBus, get_event_bus, console_subscriber

# Data
DataContract, DataEnvelope, SchemaRegistry, DataValidationError, TypedContext

# Tools
tool_contract, ToolContract

# Persistence
ProcessStatus, ProcessSchema

# Observability
TokenUsage, TelemetryCalculator

# Exceptions
FrameworkException, EngineException
```

### 3.2 REST API Endpoints (jaf/api/)

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | / | Serve SPA index.html | HTML |
| GET | /health | Health check | `{"status": "ok", "version": "0.1.0"}` |
| GET | /api/v1/demos | List available demo scenarios | Array of demo metadata |
| POST | /api/v1/demos/{demo_id}/run | Start a demo | `{process_id, stream_url}` |
| GET | /api/v1/stream/{process_id} | SSE event stream | text/event-stream |
| GET | /api/v1/processes | List processes (optional status filter) | Paginated process list |
| GET | /api/v1/processes/{id} | Get process with plan details | Process + plan steps |
| GET | /api/v1/processes/{id}/events | Get event audit trail | Chronological event list |

---

## 4. Data Models -- Database Schema

### 4.1 processes Table (migration 001)

```sql
CREATE TABLE processes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status process_status NOT NULL DEFAULT 'pending',  -- enum: pending/running/completed/failed
    current_plan JSONB NOT NULL,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Indexes: idx_processes_status, idx_processes_updated_at
```

### 4.2 llm_telemetry Table (migration 002)

```sql
CREATE TABLE llm_telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id UUID NOT NULL,
    actor_name TEXT NOT NULL,
    engine TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    total_tokens INT NOT NULL,
    latency_ms INT NOT NULL,
    cost_usd NUMERIC(12, 6) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Indexes: process_id, actor_name, created_at
```

### 4.3 process_events Table (migration 003)

```sql
CREATE TABLE process_events (
    id UUID PRIMARY KEY,
    process_id UUID NOT NULL REFERENCES processes(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(255) NOT NULL,
    message TEXT,
    status process_event_status NOT NULL,  -- enum: complete/error
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Index: (process_id, created_at)
```

---

## 5. Configuration

### 5.1 Environment Variables (env.example)

| Variable | Default | Purpose |
|----------|---------|---------|
| DEBUG | false | Verbose logging |
| LOG_LEVEL | INFO | Logging threshold |
| API_HOST | 0.0.0.0 | API bind address |
| API_PORT | 8000 | API bind port |
| CORS_ORIGINS | localhost:3000,localhost:8080 | Allowed CORS origins |
| DATABASE_URL | postgresql+asyncpg://jaf:jaf_password@localhost:5432/jaf | Database connection |
| DB_POOL_SIZE | 5 | Connection pool size |
| DB_MAX_OVERFLOW | 10 | Pool overflow limit |
| OPENAI_API_KEY | (required) | OpenAI API authentication |
| DEFAULT_MODEL | gpt-4o-mini | Default LLM model |
| DEFAULT_TEMPERATURE | 0.0 | Sampling temperature |
| LLM_TIMEOUT | 60 | LLM request timeout (seconds) |
| LLM_MAX_RPM | 10 | Rate limit (requests/minute) |
| DEFAULT_ENGINE | crewai | Engine selection |
| CREWAI_VERBOSE | false | CrewAI debug output |
| ENABLE_PERSISTENCE | true | Database persistence toggle |
| ENABLE_EVENTS | true | EventBus toggle |
| ENABLE_METRICS | false | Prometheus metrics toggle |

### 5.2 Build Configuration (pyproject.toml)

| Setting | Value |
|---------|-------|
| Build backend | hatchling |
| Package name | jaf-framework |
| Python | >=3.11 |
| Wheel packages | ["framework"] |
| CLI entry point | jaf = framework.cli.main:app |
| Black line-length | 88 |
| Black target | py311 |
| Mypy python_version | 3.11 |
| Mypy excludes | tests/, examples/, migrations/, agents/ |

---

## 6. Error Handling

### 6.1 Exception Hierarchy

```
Exception
  ├── FrameworkException          # Base for all framework errors
  │   ├── EngineException         # Engine-level failures
  │   └── StepTimeoutError        # Step execution timeout (inherits TimeoutError)
  ├── InvalidTransitionError      # Invalid state machine transition
  └── DataValidationError         # Data contract validation failure
```

### 6.2 Retry and Recovery Mechanisms

- **Step timeout**: Each `execute_step()` call is wrapped in `asyncio.wait_for(timeout=step_timeout)`. On timeout, `StepTimeoutError` is raised with step and process metadata.
- **Retry policy**: Retries apply only for exception types in `retry_on`. Default: `(ConnectionError, TimeoutError)`. Total attempts = `1 + max_retries`. Backoff: `retry_delay * 2^(attempt-1)`.
- **Process resume**: `Orchestrator.resume(process_id)` loads persisted state. Steps left in `executing` status are reset to `pending`. Execution continues from the first non-completed step.

---

## 7. Security Considerations

### 7.1 Implemented

- Input sanitization in `agents/orchestrator/utils.py`: HTML tag stripping, SQL keyword detection, length limits on tool parameters.
- Parameterized SQL queries in ProcessRepository (string interpolation uses hardcoded column names, not user input).
- Environment variable isolation via `.env` file (excluded from Git via .gitignore).
- CORS configuration (currently set to allow all origins for demo purposes).

### 7.2 Not Implemented

- Authentication and authorization on API endpoints.
- Role-based access control (RBAC).
- Rate limiting on API endpoints.
- Secrets management (API keys stored as plain environment variables).
- Audit logging for API access.
- HTTPS enforcement (delegated to reverse proxy).

---

## 8. Testing

### 8.1 Test Structure

```
tests/
├── unit/                         # 17 files
│   ├── test_actors.py            # Actor + ActorRegistry
│   ├── test_orchestrator.py      # Orchestrator with mocked engine/repo
│   ├── test_orchestrator_dry_run.py
│   ├── test_orchestrator_retry_policy.py
│   ├── test_orchestrator_step_timeout.py
│   ├── test_native_engine.py     # NativeEngine execution
│   ├── test_native_engine_parallel.py
│   ├── test_engine_factory.py    # EngineFactory selection logic
│   ├── test_state_machine.py     # State transitions
│   ├── test_types.py             # Pydantic model validation
│   ├── test_llm_config.py        # LLMConfig model
│   ├── test_data_contracts.py    # DataContract + DataEnvelope
│   ├── test_tool_contract.py     # @tool_contract decorator
│   ├── test_typed_context.py     # TypedContext operations
│   ├── test_health.py            # Health check
│   ├── test_lineage.py           # Data lineage tracking
│   └── test_vertexai_generate.py # VertexAI plan generation
├── integration/                  # 7 files (most excluded from default run)
│   ├── test_traditional_automation.py  # Active
│   ├── test_crash_recovery.py          # Excluded (requires PostgreSQL)
│   ├── test_end_to_end.py              # Excluded
│   ├── test_end_to_end_workflow.py     # Excluded
│   ├── test_etl_fixtures.py           # Active
│   ├── test_event_bus_db_subscriber.py # Excluded
│   └── test_llm_telemetry_persistence.py # Excluded
├── persistence/
│   ├── test_process_repo.py      # Excluded
│   └── test_process_event_schema.py
├── test_event_bus.py             # EventBus unit tests
├── test_deprecation.py           # Deprecation decorator tests
├── test_logging.py               # Structured logging tests
├── test_cookbook_recipes.py       # Cookbook pattern tests
└── conftest.py                   # Shared fixtures (async_session, session_maker)
```

### 8.2 Test Execution

```bash
# Run all active tests
pytest

# Run with coverage
pytest --cov=framework --cov=agents --cov-report=html

# Run a specific test file
pytest tests/unit/test_actors.py -v

# Run a specific test by name
pytest tests/unit/test_orchestrator.py -k "test_run_success" -v
```

### 8.3 Excluded Tests

The following tests are excluded via `pyproject.toml [tool.pytest.ini_options] addopts`:

| File | Reason |
|------|--------|
| tests/test_adapters/test_crewai.py | Deprecated API |
| tests/test_core/test_actor.py | Old API |
| tests/test_core/test_engine.py | Old API |
| tests/test_core/test_models.py | Old API |
| tests/integration/test_event_bus_db_subscriber.py | Requires PostgreSQL |
| tests/persistence/test_process_repo.py | Requires PostgreSQL |
| tests/integration/test_crash_recovery.py | Requires PostgreSQL |
| tests/integration/test_end_to_end.py | Requires PostgreSQL |
| tests/integration/test_end_to_end_workflow.py | Requires PostgreSQL |
| tests/integration/test_llm_telemetry_persistence.py | Requires PostgreSQL |
| tests/test_crash_recovery_resume.py | Requires PostgreSQL |

---

## 9. CI/CD Pipeline (.gitlab-ci.yml)

| Stage | Job | Description | Failure Handling |
|-------|-----|-------------|-----------------|
| lint | lint:ruff | `ruff check .` | Blocking |
| lint | lint:black | `black --check --diff .` | Blocking |
| test | test:pytest | Full test suite with coverage (SQLite) | Blocking |
| build | build:package | `python -m build` | Blocking |
| deploy | pages | MkDocs site generation (branch: init) | Non-blocking |
| deploy | publish-package | Twine upload to GitLab PyPI (on semver tag) | Allow failure |

**Test database**: CI uses `DATABASE_URL=sqlite+aiosqlite:///./test.db` to avoid PostgreSQL dependency.

**Coverage**: Cobertura XML artifact with 30-day retention. Coverage regex: `/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/`

**Package publishing**: Triggered on tags matching `^v\d+\.\d+\.\d+$`. Publishes to GitLab Package Registry via `twine upload`.
