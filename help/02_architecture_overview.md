# 02 -- Architecture Overview

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, commit 9cbda91

---

## 1. High-Level Architecture

JAF implements a three-layer architecture with three execution modes, two package trees, and a shared persistence and observability substrate.

```
+================================================================+
|                     LAYER 1: INTERFACE                          |
|  CLI (jaf new)  |  REST API (FastAPI)  |  SPA UI (jaf/static)  |
+================================================================+
                              |
                              v
+================================================================+
|                    LAYER 2: ORCHESTRATION                       |
|                                                                 |
|  Orchestrator (framework/orchestrator.py)                       |
|    - Plan generation     - Step execution                       |
|    - Progress evaluation - Retry / Resume                       |
|    - Dry-run validation  - State transitions                    |
|                                                                 |
|  NativeAdapter (jaf/adapters/native_adapter.py)                 |
|    - Agentic loop (single agent + tools)                        |
|    - Multi-agent delegation                                     |
|    - Dynamic orchestrator with adaptive re-planning             |
+================================================================+
                              |
                              v
+================================================================+
|                     LAYER 3: ENGINES                            |
|                                                                 |
|  NativeEngine        CrewAIAdapter       VertexAIAdapter        |
|  (deterministic)     (LLM-powered)       (deprecated)           |
|                                                                 |
|  All implement EngineAbstraction ABC:                           |
|    generate_plan() -> execute_step() -> evaluate_progress()     |
+================================================================+
                              |
                              v
+================================================================+
|                     ACTOR LAYER                                 |
|                                                                 |
|  framework/actor/       agents/            jaf/demos/actors.py  |
|  (ABC + Registry)       (Business domain)  (Demo actors)        |
|                                                                 |
|  Each actor declares: name, description, goal, tools,           |
|  optional llm_config (None = deterministic)                     |
+================================================================+
                              |
                              v
+================================================================+
|                   CROSS-CUTTING CONCERNS                        |
|                                                                 |
|  Persistence       EventBus         Observability               |
|  (PostgreSQL)      (pub/sub)        (telemetry, logging)        |
|                                                                 |
|  Data Contracts    State Machine    Tool Contracts               |
|  (Pydantic v2)     (transitions)   (@tool_contract)             |
+================================================================+
```

---

## 2. Two Package Trees

The codebase contains two distinct package trees with different responsibilities:

### 2.1 framework/ -- Core Library

**Package name**: `jaf-framework` (published wheel)
**Role**: Reusable, engine-agnostic automation framework.
**Import pattern**: `from framework import Actor, Orchestrator, Plan, ...`

| Sub-package | Responsibility |
|-------------|---------------|
| framework/actor/ | Actor ABC, ActorRegistry singleton |
| framework/engine/ | EngineAbstraction ABC, NativeEngine, CrewAIAdapter, VertexAIAdapter, EngineFactory |
| framework/persistence/ | PostgreSQL async ORM, ProcessRepository, event subscriber, LLM telemetry |
| framework/data/ | DataContract, TypedContext, DataEnvelope, SchemaRegistry, lineage tracking |
| framework/tools/ | ToolContract, @tool_contract decorator |
| framework/observability/ | TelemetryCalculator, TokenUsage |
| framework/cli/ | Typer CLI (jaf new, jaf --version) |
| framework/types.py | Pydantic models (Plan, PlanStep, StepResult, PlanUpdate, AgentAction, LLMConfig) |
| framework/event_bus.py | EventBus singleton with pub/sub |
| framework/orchestrator.py | Main execution coordinator (892 lines) |
| framework/state_machine.py | ProcessStateMachine |
| framework/logging.py | Structured JSON logging with ContextVar injection |
| framework/exceptions.py | FrameworkException, EngineException hierarchy |
| framework/health.py | Database health check probe |
| framework/compat.py | require_version() utility |
| framework/deprecation.py | @deprecated decorator |

### 2.2 jaf/ -- Application Layer

**Role**: Higher-level application providing API, UI, demos, and an alternative orchestration model.
**Import pattern**: `from jaf.core import Actor, ActorRegistry, ...`

| Sub-package | Responsibility |
|-------------|---------------|
| jaf/core/ | Alternative Actor/ActorRegistry with Tool decorator, EngineAbstraction re-export, ProcessState/ExecutionMode models |
| jaf/adapters/ | NativeAdapter (OpenAI Responses API engine with 3 execution modes) |
| jaf/api/ | FastAPI application: demo routes, SSE streaming, process audit endpoints |
| jaf/demos/ | 3 demo actors (CustomerIntelligence, SalesAnalytics, SmartProvisioning), mock datasets, 8 demo scenarios |
| jaf/events/ | Re-exports from framework.event_bus |
| jaf/static/ | SPA frontend (HTML, CSS, JS) for executive demonstration |

### 2.3 Relationship Between framework/ and jaf/

| Aspect | framework/ | jaf/ |
|--------|-----------|------|
| Actor semantics | Mailbox model (configure() pattern) | Tool-provider model (auto-discovery) |
| Execution | Plan-execute-evaluate lifecycle | Agentic loop / multi-agent delegation / dynamic orchestrator |
| LLM integration | Via EngineAbstraction adapters | Via OpenAI Responses API (NativeAdapter) |
| Persistence | Core feature (ProcessRepository) | Consumer (queries framework's repo) |
| UI | None | SPA with SSE streaming |
| Packaging | Wheel distribution | Application deployment |

---

## 3. Data Flow

### 3.1 Traditional Flow (NativeEngine)

```
User Goal
    |
    v
Orchestrator.run(goal, actors, context)
    |
    v
NativeEngine.generate_plan(goal, actors) --> Plan(steps=[...])
    |
    v
FOR each PlanStep:
    |
    v
NativeEngine.execute_step(step, context) --> StepResult
    |   |
    |   v
    |   ActorRegistry.get(step.actor_name).tool(step.parameters)
    |
    v
NativeEngine.evaluate_progress(plan, result) --> PlanUpdate
    |
    v
ProcessRepository.update_process(...)
    |
    v
EventBus.emit(AgentAction(...))
```

### 3.2 Agentic Flow (NativeAdapter)

```
User Goal
    |
    v
NativeAdapter.run(goal, actors, event_callback)
    |
    v
LOOP (max 15 iterations):
    |
    v
OpenAI Responses API (goal + tool schemas)
    |
    +--> Text response --> Return result
    |
    +--> Function calls --> Execute tool(s) --> Feed results back to LLM
```

### 3.3 Multi-Agent Flow (NativeAdapter)

```
User Goal
    |
    v
NativeAdapter.run_multi_agent(goal, actors)
    |
    v
PHASE 1: PLANNING (gpt-5-mini)
    |   Goal + agent descriptions --> Delegation plan
    |
    v
PHASE 2: DELEGATION (gpt-5-nano per agent)
    |   Each agent runs independently with own tools
    |
    v
PHASE 3: SYNTHESIS (gpt-5-mini)
    |   All sub-results --> Unified final answer
    |
    v
Result + audit metadata
```

---

## 4. Component Coupling Analysis

### 4.1 Low Coupling (positive)

- `framework/types.py` has zero imports from other framework modules. All other modules depend on it, but it depends on nothing internal.
- `framework/engine/engine_abstraction.py` depends only on types and actor -- clean interface.
- `framework/state_machine.py` depends only on `ProcessStatus` enum from persistence models.
- `framework/data/contracts.py` depends only on Pydantic.

### 4.2 Moderate Coupling (acceptable)

- `framework/orchestrator.py` imports from actor, engine, event_bus, persistence, state_machine, types, logging, and tools. This is expected for a coordinator component.
- `framework/engine/crewai_adapter.py` imports from CrewAI, langchain, ActorRegistry, EventBus, and types. This coupling is acceptable for an adapter.

### 4.3 High Coupling (requires attention)

- `agents/orchestrator/orchestrator_agent.py` (1,211 lines) imports from CrewAI, langchain, agents.orchestrator.llm_manager, agents.orchestrator.planning.*, agents.orchestrator.tools.*, and framework. This file exceeds recommended coupling thresholds and should be decomposed.
- `agents/orchestrator/utils.py` (`create_tool_from_method()` at 387 lines) couples dynamic class creation with input sanitization, logging, parameter extraction, and CrewAI tool construction. This function should be split.

---

## 5. Extension Points

| Extension Point | Mechanism | Location |
|----------------|-----------|----------|
| Custom engine | Implement EngineAbstraction ABC | framework/engine/ |
| Custom actor | Subclass Actor, implement configure() | framework/actor/base_actor.py |
| Custom event subscriber | Call EventBus.subscribe(handler) | framework/event_bus.py |
| Custom data contract | Subclass DataContract | framework/data/contracts.py |
| Custom tool schema | Apply @tool_contract decorator | framework/tools/contracts.py |
| Custom planner | Implement Planner protocol, register in PlannerRegistry | agents/orchestrator/planning/ |
| Custom API route | Add FastAPI router to jaf/api/main.py | jaf/api/ |

---

## 6. Critical Points

| Component | Risk | Severity |
|-----------|------|----------|
| EventBus singleton | Thread-safety gap on subscriber list initialization | Critical |
| VertexAIAdapter | Synchronous methods violate async contract | Critical |
| Orchestrator state transitions | No database transaction boundary | Critical |
| orchestrator_agent.py | 1,211 lines, excessive coupling | High |
| NativeEngine output types | Inconsistent (dict vs primitive vs DataContract) | High |
| CrewAIAdapter plan parsing | Fragile JSON extraction from LLM text output | Medium |
| ActorRegistry.get() | Calls configure() on every invocation (no caching) | Medium |
| LLM pricing | Hardcoded in telemetry.py | Low |
