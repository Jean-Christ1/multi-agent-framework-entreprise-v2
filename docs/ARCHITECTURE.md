# JAF Architecture Guide

> Jems Agent Framework - Technical Architecture Reference

## Overview

JAF (Jems Agent Framework) is a hybrid neuro-symbolic automation framework based on the Actor Model. It enables building intelligent automation systems with three execution modes:

1. **Agentic Flow**: Single orchestrator with tools (~$0.05/execution)
2. **Multi-Agent Flow**: Orchestrator + specialized actors (~$0.12/execution)
3. **Traditional Flow**: Deterministic rules, no LLM ($0.00/execution)

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 LAYER 1: ENGINE (BRAIN)                     │
│                                                             │
│   ┌─────────┐     ┌─────────┐     ┌──────────┐            │
│   │  PLAN   │ ──▶ │ EXECUTE │ ──▶ │ EVALUATE │ ──┐        │
│   └─────────┘     └─────────┘     └──────────┘   │        │
│        ▲                                          │        │
│        └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 2: ADAPTERS (MUSCLE)                     │
│                                                             │
│   ┌─────────────┐   ┌────────────┐   ┌─────────────┐      │
│   │ CrewAI      │   │ Native     │   │ LangGraph   │      │
│   │ Adapter     │   │ Adapter    │   │ (Future)    │      │
│   └─────────────┘   └────────────┘   └─────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ACTOR LAYER                              │
│                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│   │ Provisioning│   │ Habilitation│   │ Annuaire    │     │
│   │ Actor       │   │ Actor       │   │ Actor       │     │
│   └─────────────┘   └─────────────┘   └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Engine Abstraction

The `EngineAbstraction` is the core interface that all adapters implement:

```python
from framework.engine import EngineAbstraction

class EngineAbstraction(ABC):
    """The heart of JAF - manages the process lifecycle."""

    @abstractmethod
    async def generate_plan(
        self,
        goal: str,
        available_actors: List[Actor]
    ) -> Plan:
        """Phase 1: Create execution plan from goal."""
        ...

    @abstractmethod
    async def execute_step(
        self,
        step: PlanStep,
        context: Dict[str, Any]
    ) -> StepResult:
        """Phase 2: Execute a single plan step."""
        ...

    @abstractmethod
    async def evaluate_progress(
        self,
        plan: Plan,
        result: StepResult
    ) -> PlanUpdate:
        """Phase 3: Decide next action (continue/modify/abort)."""
        ...
```

### 2. EngineFactory

`EngineFactory` centralizes engine construction and selection. It supports both explicit engine selection and auto-detection based on actor configuration.

**Auto-detect rules:**
- If **all actors** have `llm_config=None` → selects `NativeEngine`
- If **any actor** has `llm_config` set → selects `CrewAIAdapter` (LLM needed for planning)

**Override:**
- `engine_type="native"` → `NativeEngine`
- `engine_type="crewai"` → `CrewAIAdapter`
- `engine_type="vertexai"` → `VertexAIAdapter` (compatibility)

Example:

```python
from framework.engine.factory import EngineFactory

engine = EngineFactory.create(
    actors=[parser_actor, generator_actor, writer_actor],
    # engine_type="native",  # optional override: "native" | "crewai" | "vertexai"
    # kwargs are forwarded to adapter constructors (e.g., LLM clients/config)
)
```

### 3. Actor

The atomic unit of functionality. An Actor encapsulates:

- **Name**: Unique identifier
- **Description**: What this actor does
- **Goal**: High-level purpose
- **Tools**: Deterministic functions (the "hands")
- **LLM Config**: Optional - `None` = deterministic actor

```python
from framework.actor import Actor
from framework.types import LLMConfig

class ProvisioningActor(Actor):
    """Actor that provisions hardware for employees."""

    def configure(self) -> None:
        self.name = "ProvisioningActor"
        self.description = "Provisions hardware for new employees"
        self.goal = "Ensure employees have required equipment"
        self.tools = [
            self.check_eligibility,
            self.select_model,
            self.create_order,
        ]
        # None = deterministic, LLMConfig(...) = uses LLM
        self.llm_config = None

    def check_eligibility(self, employee_id: str) -> bool:
        """Check if employee is eligible for equipment."""
        # Deterministic tool logic
        return True

    def select_model(self, employee_type: str) -> str:
        """Select equipment model based on role."""
        models = {"developer": "MacBook Pro", "manager": "ThinkPad"}
        return models.get(employee_type, "Standard Laptop")

    def create_order(self, model: str, employee_id: str) -> dict:
        """Create equipment order."""
        return {"order_id": "ORD-123", "model": model}
```

### 4. ActorRegistry

Singleton registry for managing actors:

```python
from framework.actor import ActorRegistry

# Register actor class
ActorRegistry.register("ProvisioningActor", ProvisioningActor)

# Get configured instance
actor = ActorRegistry.get("ProvisioningActor")

# List all registered actors
names = ActorRegistry.list()  # ["ProvisioningActor"]

# Clear registry (for testing)
ActorRegistry.clear()
```

### 5. Data Models

All Pydantic models in `framework/types.py`:

```python
from framework.types import (
    LLMConfig,      # LLM configuration
    Plan,           # Execution plan
    PlanStep,       # Single step in plan
    StepResult,     # Result of step execution
    PlanUpdate,     # Engine decision after evaluation
    AgentAction,    # Event payload
)

# LLMConfig - Optional LLM settings
config = LLMConfig(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=1000,
)

# Plan - Execution plan with steps
plan = Plan(
    steps=[
        PlanStep(
            actor_name="ProvisioningActor",
            tool_name="check_eligibility",
            parameters={"employee_id": "E123"},
        )
    ],
    status="PLANNING",  # PLANNING | EXECUTING | COMPLETED | FAILED
)

# StepResult - Outcome of step execution
result = StepResult(
    output={"eligible": True},
    status="success",  # success | error
    error=None,
)

# PlanUpdate - Engine decision
update = PlanUpdate(
    action="continue",  # continue | modify | retry | abort
    modified_plan=None,
    reason="Step completed successfully",
)

# AgentAction - Event payload
action = AgentAction(
    agentId="ProvisioningActor",
    actionType="step_completed",
    message="Eligibility check passed",
    status="complete",  # complete | error
    # timestamp auto-generated as ISO string
)
```

### 6. EventBus

In-process pub/sub for broadcasting events:

```python
from framework.event_bus import get_event_bus, console_subscriber
from framework.types import AgentAction

# Get singleton instance
bus = get_event_bus()

# Subscribe callback
bus.subscribe(console_subscriber)

# Custom subscriber
def my_handler(action):
    print(f"Received: {action.actionType}")

bus.subscribe(my_handler)

# Emit event
bus.emit(AgentAction(
    agentId="Orchestrator",
    actionType="process_started",
    message="Starting workflow",
    status="complete",
))

# Unsubscribe
bus.unsubscribe(my_handler)

# Clear all (for testing)
bus.clear()
```

**Key behaviors:**

- Broadcast to all subscribers
- Subscriber errors are logged but don't break the bus
- Thread-safe singleton

### 7. Orchestrator

The `Orchestrator` coordinates the full process lifecycle, managing Engine, Actors, EventBus, and Persistence:

```python
from framework.orchestrator import Orchestrator
from framework.engine.factory import EngineFactory
from framework.persistence.database import async_session_maker

# Create engine (auto-selected based on actor.llm_config)
engine = EngineFactory.create(
    actors=[parser_actor, generator_actor, writer_actor],
    # engine_type="native",  # optional override: "native" | "crewai" | "vertexai"
)

# Create orchestrator with engine and database session
orchestrator = Orchestrator(
    engine=engine,
    session_maker=async_session_maker,
    step_timeout=60,
    max_retries=3,
    retry_delay=5.0,
    retry_on=[ConnectionError, TimeoutError],
)

# Run orchestration
result = await orchestrator.run(
    goal="Parse BODS XML and generate test datasets",
    actors=[parser_actor, generator_actor, writer_actor],
    context={"xml_path": "docs/export-ascend.xml"},
)

# Result contains process_id, status, plan, context, and step_results
print(f"Process {result.process_id} completed with status {result.status.value}")
```

**Process Lifecycle (persisted):**

1. **PENDING** → process record is created in DB with an initial (empty) plan
2. **RUNNING** → plan is generated and steps are executed sequentially
3. **COMPLETED/FAILED** → terminal states

Within `RUNNING`, the orchestrator:
- marks each step as `executing` before running it
- updates step status to `completed` or `failed` after execution
- calls `engine.evaluate_progress(plan, result)` after each step
- may apply plan modifications if the engine returns `modify`

### Retry Policy & Step Timeouts

Step execution is protected by both a timeout and a retry policy.

**Step timeout**
- Each `execute_step` call is wrapped using `asyncio.wait_for(..., timeout=step_timeout)`.
- On timeout, a `StepTimeoutError` is raised with step/process metadata and the process is marked `FAILED`.

**Retry policy**
- Retries are applied only for retryable exception types (`retry_on`).
- Defaults to `(ConnectionError, TimeoutError)` when not provided.
- Total attempts = `1 + max_retries`.
- Backoff is exponential: `retry_delay * 2^(retry_number-1)`.
- On each retry, an event `step_retried` is emitted and progress is persisted.

### Resume Support

The orchestrator can resume an interrupted process using `resume(process_id)`:

- Loads the persisted plan/context/status from the database
- If the process is already terminal (`COMPLETED` / `FAILED`), it returns immediately
- If a step was left in `executing`, it is reset to `pending`
- Continues execution from the first step that is not `completed`
- If all steps are completed but the process status was not updated, it finalizes the process as `COMPLETED`


The orchestrator:
- Manages state transitions via `ProcessStateMachine`
- Persists process state after each step
- Emits events via `EventBus` for real-time updates
- Handles errors gracefully and updates process status

### 8. CrewAIAdapter (LLM-Powered Engine)

LLM-powered execution engine that wraps CrewAI behind the `EngineAbstraction` interface for intelligent planning and adaptive execution.

```python
from framework.engine.crewai_adapter import CrewAIAdapter
import anthropic

# Initialize with LLM client (or None for fallback planner)
client = anthropic.AsyncAnthropic(api_key="your-key")
engine = CrewAIAdapter(llm_client=client)

# Generate plan from natural language goal
plan = await engine.generate_plan(
    goal="Provision AWS EC2 instance with monitoring",
    available_actors=[provisioning_actor, monitoring_actor]
)

# Execute steps using CrewAI agents
for step in plan.steps:
    result = await engine.execute_step(step, context={})
    update = await engine.evaluate_progress(plan, result)
```

**Key Features:**
- **LLM Planning**: Analyzes goals, selects actors/tools, generates parameters
- **Multi-LLM Support**: Works with Anthropic, OpenAI, or custom clients
- **Fallback**: Uses deterministic planning if LLM unavailable
- **CrewAI Integration**: Wraps tools as CrewAI agents for execution

**Planning Flow:**
1. Analyzes available actors and their tools
2. Constructs prompt with goal and capabilities
3. Calls LLM to generate JSON plan
4. Validates and parses into `Plan` object

**Execution:**
Internally creates CrewAI agents and tasks for each step:
```python
crew_agent = Agent(
    role=actor.name,
    goal=actor.goal,
    tools=[selected_tool],
    llm=self._get_llm(actor.llm_config),
    allow_delegation=False
)
```

**Progress Evaluation:**
- ✓ Success + Output → Continue
- ✗ Error → Abort
- ⚠️ Success + No Output → Modify (re-plan)

**CrewAIAdapter vs NativeEngine:**

| Feature | CrewAIAdapter | NativeEngine |
|---------|---------------|--------------|
| Planning | LLM-powered | Pre-built/sequential |
| Cost | LLM API costs | Free |
| Speed | Slower | Faster |
| Best for | Complex reasoning | Deterministic ETL |

**Use when:**
- Goals require natural language interpretation
- Complex workflows need adaptive planning
- Actor capabilities change dynamically

**Avoid when:**
- High-volume, low-latency needed
- Fixed, deterministic workflows
- Offline/air-gapped environments

### 9. NativeEngine

A deterministic execution engine that doesn't use LLM. Ideal for actors with `llm_config=None`:

```python
from framework.engine import NativeEngine
from framework.types import Plan, PlanStep

# Option 1: Use pre-built plan
plan = Plan(
    steps=[
        PlanStep(actor_name="ParserActor", tool_name="parse_xml", parameters={"path": "data.xml"}),
        PlanStep(actor_name="GeneratorActor", tool_name="generate_data", parameters={"count": 100}),
    ],
    status="PLANNING",
)
engine = NativeEngine(default_plan=plan)

# Option 2: Let engine generate sequential plan from actor tools
engine = NativeEngine()
plan = await engine.generate_plan("Generate test data", [parser_actor, generator_actor])

# Execute steps
for step in plan.steps:
    result = await engine.execute_step(step, context={})
    update = await engine.evaluate_progress(plan, result)
```

**Key differences from CrewAI Adapter:**

- **No LLM**: Direct tool execution, no AI agent wrappers
- **Deterministic**: Same inputs = same outputs
- **Fast**: No API calls, no token costs
- **Config-driven**: Uses pre-built plans or simple sequential generation

**Use cases:**

- ETL pipelines with deterministic transformations
- Data generation for testing
- Rule-based workflows
- High-volume, low-cost automation

### 10. ProcessStateMachine

Manages valid state transitions for process execution with validation:

```python
from framework.state_machine import ProcessStateMachine, InvalidTransitionError
from framework.persistence.models import ProcessStatus

# Check if transition is valid
can_transition = ProcessStateMachine.can_transition(
    ProcessStatus.PENDING,
    ProcessStatus.RUNNING
)  # True

# Validate transition (raises if invalid)
try:
    ProcessStateMachine.validate_transition(
        ProcessStatus.COMPLETED,
        ProcessStatus.RUNNING
    )
except InvalidTransitionError as e:
    print(f"Invalid: {e}")  # Cannot transition from COMPLETED to RUNNING

# Get valid transitions from a state
valid = ProcessStateMachine.get_valid_transitions(ProcessStatus.RUNNING)
# {ProcessStatus.COMPLETED, ProcessStatus.FAILED}

# Check if state is terminal
is_terminal = ProcessStateMachine.is_terminal(ProcessStatus.COMPLETED)  # True
```

**State Diagram:**

```
        PENDING
           │
           ├───> RUNNING ───┬──> COMPLETED (terminal)
           │                │
           └───> FAILED <───┘ (terminal)
```

**Valid Transitions:**

- `PENDING` → `RUNNING` or `FAILED`
- `RUNNING` → `COMPLETED` or `FAILED`
- `COMPLETED` → (no transitions, terminal)
- `FAILED` → (no transitions, terminal)

The state machine ensures processes can only transition through valid states, preventing invalid state changes.

### 11. Persistence

Process state is persisted in PostgreSQL:

```python
from framework.persistence.process_repo import ProcessRepository
from framework.persistence.models import ProcessStatus

# Create repository with async session
repo = ProcessRepository(session)

# Create process
process = await repo.create_process(
    process_id=uuid.uuid4(),
    plan=plan,
    context={"employee_id": "E123"},
    status=ProcessStatus.PENDING,
)

# Update process
await repo.update_process(
    process_id=process.id,
    plan=updated_plan,
    context={"result": "success"},
    status=ProcessStatus.COMPLETED,
)

# Load process
loaded = await repo.get_process(process.id)

# List by status
pending = await repo.list_processes(status=ProcessStatus.PENDING)
```

**Database schema:**

```sql
CREATE TABLE processes (
    id UUID PRIMARY KEY,
    status process_status NOT NULL,  -- pending/running/completed/failed
    current_plan JSONB NOT NULL,
    context JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## File Structure

```
jaf-framework/
├── framework/                 # Core framework
│   ├── __init__.py           # Type exports
│   ├── types.py              # Pydantic models
│   ├── event_bus.py          # EventBus singleton
│   ├── orchestrator.py      # Orchestrator coordinator
│   ├── state_machine.py      # ProcessStateMachine
│   ├── exceptions.py      # Framework exceptions
│   ├── actor/
│   │   ├── __init__.py       # Actor, ActorRegistry exports
│   │   ├── base_actor.py     # Actor ABC
│   │   └── registry.py       # ActorRegistry
│   ├── engine/
│   │   ├── __init__.py       # EngineAbstraction export
│   │   ├── engine_abstraction.py
│   │   ├── crewai_adapter.py     # LLM-based engine
│   │   ├── factory.py       # EngineFactory
│   │   ├── vertexai_adapter.py     # Vertex AI-backed engine adapter
│   │   └── native_engine.py      # Deterministic engine
│   ├── observability/
│   │   ├── telemetry.py       # Telemetry helpers
│   └── persistence/
│       ├── __init__.py
│       ├── database.py       # Async connection
│       ├── event_bus_subscriber.py       # Persists/forwards EventBus events
│       ├── llm_telemetry_repo.py       # Repository for storing LLM telemetry (tokens/cost/latency, if tracked)
│       ├── models.py         # SQLAlchemy models
│       ├── schemas.py        # Pydantic schemas
│       └── process_repo.py   # Repository
├── agents/                    # Business actors
│   ├── __init__.py           # Agent exports
│   ├── provisionning_agent.py
│   ├── piramid_agent.py
│   ├── geai_agent.py
│   ├── ceo_agent.py
│   ├── annuaire_agent.py
│   └── habilitation_agent.py
│
├── examples/                         # Usage examples
│   ├── agentic_flow.py               # Agentic flow demo
│   ├── event_bus_flow.py             # EventBus demo
│   ├── multi_agent_flow.py           # Multi Agent flow demo
│   ├── simple_actor_example.py       # Simple actor demo
│   ├── traditional_automation_complete.py       # Traditional automation demo
│   ├── traditional_flow.py           # Traditional flow demo
│   └── etl_demo/                     # ETL demo (BODS XML parsing)
│       ├── actors.py                 # BODSParserActor, DataGeneratorActor, ParquetWriterActor
│       └── run_demo.py               # Demo entry point
├── tests/                     # Test suite
├── migrations/                # SQL migrations
└── docs/                      # Documentation
```

## Execution Modes

### Agentic Flow

- Single actor handles entire goal
- Uses multiple tools internally
- Best for simple, focused tasks
- Cost: ~$0.05

### Multi-Agent Flow

- Orchestrator delegates to specialized actors
- Each actor has its own tools and expertise
- Best for complex, multi-domain tasks
- Cost: ~$0.12

### Traditional Flow

- No LLM involvement (`llm_config = None`)
- Pure rules-based execution
- Best for deterministic processes
- Cost: $0.00

## Current Implementation Notes

Key points:

1. **Orchestrator loop is implemented**
   - Runs the full lifecycle: plan → execute steps → evaluate → finish
   - Persists plan + context after key transitions and after every step
   - Emits events via the in-process `EventBus`

2. **Resume is supported**
   - Processes can resume from the last persisted state
   - If a step was left in `executing`, it is reset to `pending` on resume
   - Processes store `current_plan` and `context` as JSONB
   - Updates typically overwrite the persisted plan/context snapshot (simpler and robust for recovery)

3. **Persistence remains PostgreSQL + JSONB**
   - `current_plan` and `context` are stored as JSONB snapshots

4. **Engine selection is centralized**
   - `EngineFactory` auto-selects `NativeEngine` vs `CrewAIAdapter` based on actor `llm_config`
   - Supports explicit override: `native`, `crewai`, `vertexai`

5. **Resilience**
   - Step timeout via `asyncio.wait_for(..., timeout=step_timeout)`
   - Retry policy with exponential backoff (`retry_delay * 2^(n-1)`)
   - Retryable exception types configurable via `retry_on`



## Import Reference

```python
# Types
from framework.types import (
    LLMConfig,
    Plan,
    PlanStep,
    StepResult,
    PlanUpdate,
    AgentAction,
)

# Actor
from framework.actor import Actor, ActorRegistry

# Engine
from framework.engine import EngineAbstraction

# EventBus
from framework.event_bus import get_event_bus, EventBus, console_subscriber

# Persistence
from framework.persistence import ProcessStatus, ProcessSchema
from framework.persistence.process_repo import ProcessRepository
from framework.persistence.database import async_session_maker
```

## Examples

### ETL Demo

The ETL demo (`examples/etl_demo/`) demonstrates the framework's capabilities with SAP BODS XML parsing and test data generation:

- **BODSParserActor**: Parses BODS XML metadata and extracts table schemas
- **DataGeneratorActor**: Generates realistic aviation domain test data
- **ParquetWriterActor**: Writes input/expected Parquet files for ETL testing

**Usage:**

```bash
# Run ETL demo in standalone mode
python -m examples.etl_demo.run_demo --standalone

# With custom record count
python -m examples.etl_demo.run_demo --standalone --count 100
```

See [examples/etl_demo/README.md](../examples/etl_demo/README.md) for detailed documentation.

### Agentic Flow Example

The agentic flow example (`examples/agentic_flow.py`) demonstrates a single orchestrator actor using multiple tools:

- Single actor handles entire workflow
- No delegation to other agents
- Cost-effective for simple tasks

See [docs/AGENTIC_FLOW.md](AGENTIC_FLOW.md) for detailed documentation.

## See Also

- [BACKLOG.md](BACKLOG.md) - Sprint backlog and tasks
- [STREAMS.md](STREAMS.md) - Development stream plans
- [AGENTIC_FLOW.md](AGENTIC_FLOW.md) - Agentic flow pattern documentation
