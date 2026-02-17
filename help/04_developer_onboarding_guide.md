# 04 -- Developer Onboarding Guide

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, commit 9cbda91

---

## 1. Prerequisites

| Requirement | Minimum Version | Purpose |
|-------------|-----------------|---------|
| Python | 3.11+ | Runtime |
| pip | 23.0+ | Package management |
| Git | 2.30+ | Version control |
| PostgreSQL | 14+ | Persistence (optional for unit tests) |
| Operating System | Ubuntu 22.04 LTS, macOS 13+, or Windows 11 | Development platform |

---

## 2. Step-by-Step Installation

### 2.1 Clone the Repository

```bash
git clone https://gitlab.com/llm-ai-agents-agentic-ai/multi-agent-framework-entreprise-v2.git
cd multi-agent-framework-entreprise-v2
```

### 2.2 Create Virtual Environment

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 2.3 Install Dependencies

Choose the appropriate installation tier:

```bash
# Tier 1: Core only (no LLM, no cmake required)
# Use for: deterministic actors, NativeEngine, persistence
pip install -r requirements-core.txt

# Tier 2: Core + LLM support
# Use for: CrewAI adapter, OpenAI integration
pip install -r requirements-llm.txt

# Tier 3: Full installation (Core + LLM + API server)
# Use for: FastAPI API, SPA UI, complete development
pip install -r requirements.txt

# Tier 4: ETL demo extras (on top of any tier)
# Use for: running examples/etl_demo/
pip install -r requirements-demo.txt
```

### 2.4 Install in Editable Mode (Development)

```bash
pip install -e .[dev]
```

This installs the framework package in editable mode plus development tools (pytest, black, ruff, mypy, pre-commit).

### 2.5 Install Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

---

## 3. Environment Configuration

### 3.1 Create .env File

```bash
cp env.example .env
```

### 3.2 Required Variables

Edit `.env` with the following minimum configuration:

```bash
# Database (required for persistence features)
DATABASE_URL=postgresql+asyncpg://jaf:jaf_password@localhost:5432/jaf_dev

# LLM API key (required for agentic/multi-agent modes)
OPENAI_API_KEY=sk-your-api-key-here
```

### 3.3 Database Setup (Optional for Unit Tests)

For unit tests, no database is required. The CI pipeline uses SQLite:

```bash
DATABASE_URL=sqlite+aiosqlite:///./test.db
```

For full integration tests and API server usage, set up PostgreSQL:

```bash
createdb jaf_dev
psql jaf_dev < migrations/001_create_processes.sql
psql jaf_dev < migrations/002_create_llm_telemetry.sql
psql jaf_dev < migrations/003_create_process_events.sql
```

---

## 4. Local Execution

### 4.1 Run Unit Tests

```bash
# All active tests
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=framework --cov-report=html
# Open htmlcov/index.html in browser
```

### 4.2 Run a Specific Example

```bash
# Simple actor example (no LLM, no database required)
python -m examples.simple_actor_example

# Event bus demonstration
python -m examples.event_bus_flow

# Traditional automation (deterministic, no LLM)
python -m examples.traditional_flow

# ETL demo (requires requirements-demo.txt)
python -m examples.etl_demo.run_demo --standalone
```

### 4.3 Start the API Server

```bash
# Requires: requirements.txt + DATABASE_URL + OPENAI_API_KEY
uvicorn jaf.api.main:app --reload --host 0.0.0.0 --port 8000
```

Access points:
- SPA UI: http://localhost:8000/
- Health check: http://localhost:8000/health
- Demo list: http://localhost:8000/api/v1/demos
- Processes: http://localhost:8000/api/v1/processes

### 4.4 Use the CLI

```bash
# Scaffold a new project
jaf new my_project

# Show framework version
jaf --version
```

---

## 5. Debugging

### 5.1 Enable Debug Logging

Set in `.env`:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### 5.2 Enable SQL Echo

```bash
SQL_ECHO=true
```

### 5.3 Enable CrewAI Verbose Mode

```bash
CREWAI_VERBOSE=true
```

### 5.4 Common Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `ModuleNotFoundError: framework` | Package not installed | Run `pip install -e .` |
| `RuntimeError: DATABASE_URL is not set` | Missing environment variable | Create `.env` file or export `DATABASE_URL` |
| `ImportError: crewai` | LLM dependencies not installed | Install via `pip install -r requirements-llm.txt` |
| `asyncpg.InvalidCatalogNameError` | Database does not exist | Run `createdb jaf_dev` |
| `relation "processes" does not exist` | Migrations not applied | Run SQL migration files against database |
| Tests marked as `SKIPPED` | Missing optional dependencies | Install the appropriate requirement tier |

---

## 6. Recommended Git Workflow

### 6.1 Branch Naming Convention

```
feature/JAF-XX-short-description   # New feature
fix/JAF-XX-short-description       # Bug fix
tests/JAF-XX-short-description     # Test additions
```

### 6.2 Development Workflow

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/JAF-XX-description

# 2. Develop and test locally
pytest
pre-commit run --all-files

# 3. Commit changes
git add <files>
git commit -m "JAF-XX: Short description of change"

# 4. Push and create merge request
git push -u origin feature/JAF-XX-description
# Create MR via GitLab UI against main branch
```

### 6.3 Commit Message Convention

```
JAF-XX: Imperative description of change

Optional body with additional context.
Reference relevant design decisions or constraints.
```

Examples:
```
JAF-42: Add retry policy to Orchestrator step execution
JAF-81: Implement DataContract base class with Pydantic v2
JAF-99: Fix EventBus subscriber initialization race condition
```

---

## 7. Code Standards

### 7.1 Formatting and Linting

| Tool | Command | Configuration |
|------|---------|---------------|
| Black | `black .` | line-length=88, target=py311 |
| Ruff | `ruff check .` | pyproject.toml |
| Mypy | `mypy framework/` | pyproject.toml (excludes tests, examples, agents) |

### 7.2 Pre-commit Hooks

All code must pass pre-commit hooks before merging:
- Black (formatting)
- Ruff (linting with auto-fix)
- Mypy (type checking on framework/)
- Trailing whitespace removal
- End-of-file newline
- YAML/TOML validation
- Large file check (max 1000KB)
- Merge conflict detection
- Mixed line ending fix (LF)

### 7.3 Running Hooks Manually

```bash
# All files
pre-commit run --all-files

# Specific file
pre-commit run --files framework/orchestrator.py
```

---

## 8. Version Management

Version is defined in two files that must remain synchronized:

| File | Content |
|------|---------|
| `framework/_version.py` | `__version__ = "0.1.0"` and `__version_info__ = (0, 1, 0)` |
| `pyproject.toml` | `[project] version = "0.1.0"` |

Verification command:

```bash
python3 -c "
from framework._version import __version__, __version_info__
import tomllib
with open('pyproject.toml', 'rb') as f:
    pyproject = tomllib.load(f)
pkg_version = pyproject['project']['version']
assert __version__ == pkg_version, f'Mismatch: {__version__} vs {pkg_version}'
print(f'Versions match: {__version__}')
"
```
