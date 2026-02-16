# JAF - Jems Agent Framework

> A hybrid neuro-symbolic automation framework based on the Actor Model

[![Pipeline Status](https://gitlab.jems-group.com/jems/interne/jems-multi-agent-framework/jems-multi-agent-framework/badges/main/pipeline.svg)](https://gitlab.jems-group.com/jems/interne/jems-multi-agent-framework/jems-multi-agent-framework/-/pipelines)
[![Coverage](https://gitlab.jems-group.com/jems/interne/jems-multi-agent-framework/jems-multi-agent-framework/badges/main/coverage.svg)](https://gitlab.jems-group.com/jems/interne/jems-multi-agent-framework/jems-multi-agent-framework/-/graphs/main/charts)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

JAF is an enterprise-grade automation framework that enables building intelligent automation systems with three execution modes:

| Mode            | Description                       | Cost   | Use Case                    |
| --------------- | --------------------------------- | ------ | --------------------------- |
| **Agentic**     | Single orchestrator + tools       | ~$0.05 | Simple, focused tasks       |
| **Multi-Agent** | Orchestrator + specialized actors | ~$0.12 | Complex, multi-domain tasks |
| **Traditional** | Deterministic rules, no LLM       | $0.00  | Rule-based automation       |

### Key Features

- **Vendor Independence**: Swap between CrewAI, LangGraph, or custom engines
- **Cost Optimization**: Choose the right mode for each task
- **Actor Model**: Share-nothing architecture with clear boundaries
- **Event-Driven**: Real-time updates via EventBus
- **Crash Recovery**: Persistent process state in PostgreSQL

### Installation

#### Option 1: From GitLab Package Registry (Recommended for Production)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from GitLab Package Registry
pip install jaf-framework --index-url https://gitlab.jems-group.com/api/v4/projects/<PROJECT_ID>/packages/pypi/simple
```

Or add to your `requirements.txt`:

```txt
--extra-index-url https://gitlab.jems-group.com/api/v4/projects/<PROJECT_ID>/packages/pypi/simple
jaf-framework>=0.1.0
```

**Note:** Replace `<PROJECT_ID>` with the actual GitLab project ID. You can find this in your project's Settings > General.

#### Option 2: From Source (For Development)

```bash
# Clone the repository
git clone https://gitlab.jems-group.com/jems/interne/jems-multi-agent-framework/jems-multi-agent-framework.git
cd jems-multi-agent-framework

# Create virtual environment
python -m venv venv # On Windows
python3 -m venv venv # On macOS
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (choose one tier)

# Core only (no LLM, no cmake required)
# Minimal runtime to build & run basic actors and the event bus.
pip install -r requirements-core.txt

# With LLM support
# Adds LLM-related dependencies (providers, tokenizers, etc.) on top of core.
pip install -r requirements-llm.txt

# Full installation (all features)
# Everything: core + LLM + any extra integrations/tools bundled in the project.
pip install -r requirements.txt

# Set up environment
cp env.example .env
# Edit .env with your DATABASE_URL and API keys
```

### Database Setup

```bash
# Ensure PostgreSQL is running locally
# Create database
createdb jaf_dev

# Run migration
psql jaf_dev < migrations/001_create_processes.sql

# Set environment variable
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/jaf_dev"
```

### Optional: ETL Demo

The ETL demo (`examples/etl_demo/`) demonstrates the framework's capabilities with SAP BODS XML parsing and test data generation. It requires additional dependencies:

```bash
# Install demo dependencies
pip install -r requirements-demo.txt

# Run the demo
python -m examples.etl_demo.run_demo --standalone
```

**Note:** The core framework (`import framework`) works without demo dependencies. Demo dependencies are only needed if you want to run the ETL demo examples.

## CLI Usage

You can use the JAF CLI to scaffold new projects and check the framework version.

### Installation

Install the CLI in editable mode (for development):

```bash
pip install -e .
```

### Commands

- Create a new project:
    ```bash
    jaf new my_project
    ```
    or

    ```bash
    jaf new my-project
    ```

- Show the framework version:
    ```bash
    jaf --version
    ```


JAF provides a CLI tool to scaffold new projects with the recommended structure.

This will create a new directory `my-project/` with the following structure:

```
my-project/
├─ my_actors/
│  ├─ __init__.py
│  └─ sample_actor.py
├─ workflows/
│  ├─ __init__.py
│  └─ sample_workflow.py
├─ tests/
│  ├─ __init__.py
│  └─ test_sample_actor.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

Each generated file contains a minimal, working example compatible with the JAF framework. See the generated README.md for usage instructions in your new project.

To see available CLI commands:

```bash
jaf --help
```


### Your First Actor

```python
from framework import Actor, ActorRegistry, LLMConfig

class GreeterActor(Actor):
    """An actor that greets people."""

    def configure(self) -> None:
        self.name = "GreeterActor"
        self.description = "Greets people in different languages"
        self.goal = "Provide personalized greetings"
        self.tools = [self.greet]
        self.llm_config = None  # Deterministic actor

    def greet(self, name: str, language: str = "en") -> str:
        """Greet someone by name."""
        greetings = {
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!",
            "fr": f"Bonjour, {name}!",
        }
        return greetings.get(language, greetings["en"])


# Register the actor
ActorRegistry.register("GreeterActor", GreeterActor)

# Retrieve a configured instance
actor = ActorRegistry.get("GreeterActor")
print(actor.greet("Alice", "fr"))  # Bonjour, Alice!
```

### Using the EventBus

```python
from framework import get_event_bus, console_subscriber, AgentAction

# Get singleton bus
bus = get_event_bus()

# Subscribe to events
bus.subscribe(console_subscriber)

# Emit events
bus.emit(AgentAction(
    agentId="GreeterActor",
    actionType="greeting_sent",
    message="Greeted Alice in French",
    status="complete",
))
```

### Run Examples

```bash
# Simple Actor Tutorial (start here)
python examples/simple_actor_example.py
# macOS / Linux
python3 -m examples.simple_actor_example

# EventBus demonstration
python examples/event_bus_flow.py
# macOS / Linux
python3 -m examples.event_bus_flow

```

## Building Your Project

When using JAF as a template for your project:

### Recommended Structure

my-automation-project/
├── framework/ # JAF core (keep as-is)
├── my_actors/ # Your custom actors
│ ├── **init**.py
│ └── my_actor.py
├── workflows/ # Your workflow definitions
│ └── main_workflow.py
├── tests/
│ └── test_my_actor.py
├── requirements.txt # Your project deps + JAF deps
└── README.md

### What to Customize

| Directory    | Action                             |
| ------------ | ---------------------------------- |
| `framework/` | Keep unchanged - core JAF          |
| `agents/`    | Replace with your actors or remove |
| `examples/`  | Use as reference, then remove      |
| `tests/`     | Add your tests alongside JAF tests |

### Quick Start Template

# my_actors/hello_actor.py

from framework import Actor, ActorRegistry

class HelloActor(Actor):
def configure(self):
self.name = "HelloActor"
self.description = "My first actor"
self.goal = "Say hello"
self.tools = [self.greet]
self.llm_config = None

    def greet(self, name: str) -> str:
        return f"Hello, {name}!"

# Register and use

ActorRegistry.register("HelloActor", HelloActor)

actor = ActorRegistry.get("HelloActor")
print(actor.greet("World"))

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 LAYER 1: ENGINE (BRAIN)                     │
│         PLAN ──▶ EXECUTE ──▶ EVALUATE ──┐                   │
│           ▲                             │                   │
│           └─────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 2: ADAPTERS (MUSCLE)                     │
│         CrewAI  │  Native  │  LangGraph (Future)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ACTOR LAYER                              │
│    Provisioning  │  Identity  │  Email  │  Custom...        │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
jaf-framework/
├── framework/                 # Core framework package
│   ├── __init__.py           # Exports: LLMConfig, Plan, PlanStep, etc.
│   ├── types.py              # Pydantic models (Plan, AgentAction, etc.)
│   ├── event_bus.py          # EventBus singleton
│   ├── actor/
│   │   ├── __init__.py       # Exports: Actor, ActorRegistry
│   │   ├── base_actor.py     # Actor ABC
│   │   └── registry.py       # ActorRegistry singleton
│   ├── engine/
│   │   ├── __init__.py       # Exports: EngineAbstraction
│   │   ├── engine_abstraction.py  # Engine ABC
│   │   ├── crewai_adapter.py      # CrewAI implementation (Week 2)
│   │   └── native_engine.py       # Native implementation (Week 3)
│   ├── orchestrator/         # Orchestrator logic, session, planning, tools
│   │   ├── __init__.py
│   │   ├── orchestrator_agent.py
│   │   ├── llm_manager.py
│   │   ├── scenario_classifier.py
│   │   ├── session.py
│   │   ├── models.py
│   │   ├── utils.py
│   │   ├── planning/         # Planning submodule
│   │   └── tools/            # Orchestrator tools
│   ├── cli/                  # CLI entry point (main.py, scaffolder.py)
│   │   ├── main.py
│   │   └── scaffolder.py
│   ├── data/                 # Data contracts, schema registry, validation, lineage
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   ├── schema_registry.py
│   │   ├── validation.py
│   │   └── lineage.py        # Optional data lineage tracking
│   ├── observability/        # Telemetry, logging, metrics
│   ├── persistence/
│   │   ├── __init__.py       # Exports: ProcessStatus, ProcessSchema
│   │   ├── database.py       # Async SQLAlchemy connection
│   │   ├── models.py         # ORM models
│   │   ├── schemas.py        # Pydantic schemas
│   │   └── process_repo.py   # Repository (raw SQL)
│   ├── tools/                # Tool contracts
│   ├── _version.py           # Version info
│   ├── compat.py             # Compatibility helpers
│   ├── deprecation.py        # Deprecation warnings
│   ├── exceptions.py         # Framework exceptions
│   └── state_machine.py      # Process state machine
├── agents/                    # Business actors
│   ├── provisionning_agent.py    # Hardware provisioning actor
│   ├── annuaire_agent.py         # Directory services actor
│   └── ...
├── examples/                  # Usage examples
│   ├── event_bus_flow.py
│   ├── agentic_flow.py
│   └── multi_agent_flow.py
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── persistence/           # Database tests
├── migrations/
│   └── 001_create_processes.sql  # Database schema
├── docs/
│   ├── ARCHITECTURE.md        # This guide
│   ├── BACKLOG.md             # Sprint tasks
│   └── diagrams/              # Architecture diagrams
├── requirements.txt
└── README.md
```

## Core Contracts

### EngineAbstraction

```python
from framework.engine import EngineAbstraction

class EngineAbstraction(ABC):
    async def generate_plan(goal: str, available_actors: List[Actor]) -> Plan
    async def execute_step(step: PlanStep, context: Dict) -> StepResult
    async def evaluate_progress(plan: Plan, result: StepResult) -> PlanUpdate
```

### Actor

```python
from framework.actor import Actor

class Actor(ABC):
    name: str
    description: str
    goal: str
    tools: List[Callable]
    llm_config: Optional[LLMConfig]  # None = deterministic

    def configure(self) -> None:
        """Set up actor metadata and tools."""
        ...
```

### Data Models

```python
from framework.types import Plan, PlanStep, StepResult, PlanUpdate, AgentAction, LLMConfig

# Plan execution
plan = Plan(steps=[...], status="PLANNING")
result = StepResult(output={...}, status="success")
update = PlanUpdate(action="continue", reason="Step succeeded")

# Events
action = AgentAction(
    agentId="MyActor",
    actionType="step_completed",
    message="Task finished",
    status="complete",
)
```

## Configuration

Set environment variables in `.env`:

```bash
# Required for database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/jaf_dev

# Optional: Enable SQL logging
SQL_ECHO=false

# Required for LLM operations
OPENAI_API_KEY=sk-your-key-here
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=framework --cov-report=html

# Run specific tests
pytest tests/unit/test_actors.py -v
pytest tests/test_event_bus.py -v
```

## Sprint 1 Status (Foundation)

| Component                       | Status      | Ticket         |
| ------------------------------- | ----------- | -------------- |
| Plan/PlanStep/StepResult models | ✅ Complete | JAF-3, JAF-5   |
| LLMConfig                       | ✅ Complete | JAF-17         |
| Actor ABC                       | ✅ Complete | JAF-16         |
| ActorRegistry                   | ✅ Complete | JAF-18, JAF-20 |
| EngineAbstraction               | ✅ Complete | JAF-3          |
| ProcessRepository               | ✅ Complete | JAF-26         |
| EventBus                        | ✅ Complete | JAF-28         |
| AgentAction                     | ✅ Complete | JAF-29         |

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - Technical reference
- [Sprint Backlog](docs/BACKLOG.md) - Tasks and milestones
- [Stream Plans](docs/STREAMS.md) - Development timeline
- [Migration Guide](docs/MIGRATION.md) - Upgrade steps and breaking change migration notes
- [Cookbook – Common Patterns](docs/COOKBOOK.md) - Practical recipes and usage patterns
- [Health Check](docs/HEALTH_CHECK.md) - Database connectivity probe for monitoring/K8s
- [Data Lineage](docs/DATA_LINEAGE.md) - Track data provenance through workflows (optional, disabled by default)
- [Live Documentation & API Reference](docs/API_REFERENCE.md) — Docs link will be available after first GitLab Pages deploy (can be run locally with `mkdocs serve`)

## Tool Contract & Schema Integration

JAF standardizes tool schema declaration and extraction for documentation, validation, and integration:

- Use the `@tool_contract` decorator (from `framework.tools.contracts`) on your tool methods to declare input/output schemas (must be DataContract subclasses).
- The `ToolContract` class provides a standard interface (`to_schema_dict()`) for schema extraction, used by the registry and engine.
- `SchemaRegistry` (from `framework.data.schema_registry`) collects all tool schemas and can export them as JSON or OpenAPI 3.0.
- The engine (NativeEngine) can access tool schemas at runtime for documentation or validation via `get_tool_schema(actor, tool)`.

**Example:**

```python
from framework.tools.contracts import tool_contract
from framework.data.contracts import DataContract

class MyInput(DataContract):
    ...
class MyOutput(DataContract):
    ...

class MyActor(Actor):
    ...
    @tool_contract(input=MyInput, output=MyOutput)
    def my_tool(self, data: MyInput) -> MyOutput:
        ...
```

**OpenAPI Export:**

```python
from framework.data.schema_registry import SchemaRegistry
openapi_spec = SchemaRegistry.export_openapi()
```

- Each tool is mapped to a POST endpoint under `/actors/{actor}/{tool}`.
- Input/output schemas are registered as OpenAPI components.

See `framework/tools/contracts.py` and `framework/data/schema_registry.py` for details and extension.

## Contributing

1. Pick a task from [BACKLOG.md](docs/BACKLOG.md)
2. Create a feature branch: `feature/JAF-XX-description`
3. Implement with tests
4. Submit MR for review against `init` branch

---

Built with ❤️ by the JEMS Innovation Team
