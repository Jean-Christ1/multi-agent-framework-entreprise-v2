# 06 -- Agent Framework Deep Analysis

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, commit 9cbda91

---

## 1. Framework Purpose

JAF provides a unified orchestration layer for building automation systems that combine deterministic business rules with LLM-driven reasoning. The framework solves the following problems:

- **Vendor lock-in**: Business logic is decoupled from execution engines. The same actors work with CrewAI, OpenAI Responses API, or pure deterministic execution.
- **Cost optimization**: Each workflow selects the cheapest execution mode that meets its requirements (Traditional at $0, Agentic at ~$0.05, Multi-Agent at ~$0.12).
- **Crash recovery**: Process state is persisted after every step. Interrupted processes can resume from the last checkpoint.
- **Observability**: Every step emits events via EventBus. Structured JSON logging with ContextVar injection provides per-process, per-actor, per-step traceability.

---

## 2. Multi-Agent Architecture

### 2.1 Actor Model

Actors follow a share-nothing architecture inspired by the Erlang Actor Model:

- Each Actor encapsulates its own state, tools, and optional LLM configuration.
- Actors communicate only through the Orchestrator (no direct actor-to-actor messaging).
- An Actor declares its capabilities via `configure()`: name, description, goal, tools (list of callables), and optional `llm_config`.
- If `llm_config` is `None`, the actor is deterministic. If set, the actor is LLM-enabled.

### 2.2 Two Actor Implementations

| Property | framework/actor/ | jaf/core/actor.py |
|----------|-----------------|-------------------|
| Pattern | ABC with configure() hook | ABC with auto-discovery via @Tool decorator |
| Tool declaration | Explicit list in configure() | Auto-discovered from decorated methods |
| Tool schema | Via @tool_contract decorator (optional) | Auto-generated OpenAI function schema from type annotations |
| Registry | Class-level singleton (classmethods) | Instance-level singleton |
| Instantiation | ActorRegistry.get() calls configure() | Constructor auto-calls _discover_tools() |
| Primary consumer | framework/orchestrator.py, NativeEngine, CrewAIAdapter | jaf/adapters/native_adapter.py (OpenAI Responses API) |

### 2.3 Actor Registry

```python
# framework/ pattern
ActorRegistry.register("MyActor", MyActorClass)
actor = ActorRegistry.get("MyActor")  # Instantiates + configure()
names = ActorRegistry.list()
ActorRegistry.clear()  # For testing

# jaf/ pattern
registry = ActorRegistry()
registry.register(my_actor_instance)
actor = registry.get("MyActor")
```

---

## 3. Orchestrator

### 3.1 framework/orchestrator.py (892 lines)

The Orchestrator is the central coordinator. Its lifecycle:

1. **Process creation**: Generates UUID, creates PENDING record in database.
2. **Plan generation**: Delegates to the engine's `generate_plan()` method.
3. **Step execution loop**: For each PlanStep:
   - Marks step as `executing`
   - Calls `engine.execute_step(step, context)` with timeout
   - On success: updates step status, stores result in context
   - On retryable failure: exponential backoff retry
   - On terminal failure: marks process as FAILED
   - Calls `engine.evaluate_progress(plan, result)` for decision
4. **Persistence**: Saves plan + context to database after every step.
5. **Event emission**: Broadcasts AgentAction events via EventBus.

### 3.2 jaf/adapters/native_adapter.py (1,050 lines)

The NativeAdapter provides three execution modes using the OpenAI Responses API:

**Mode 1: Agentic (run)**
- Single LLM agent with access to all actor tools.
- Iterative loop: LLM requests tool calls, tools execute, results feed back.
- Maximum 15 iterations.
- Model: gpt-5-nano (default).

**Mode 2: Multi-Agent Delegation (run_multi_agent)**
- Phase 1 (Planning): gpt-5-mini analyzes goal and produces delegation plan.
- Phase 2 (Delegation): Each agent receives a sub-goal, runs independently with its own tools via gpt-5-nano.
- Phase 3 (Synthesis): gpt-5-mini consolidates all sub-results into a unified answer.
- No inter-agent communication; all coordination via orchestrator.

**Mode 3: Dynamic Orchestrator (run_dynamic)**
- Phase 1 (Discovery): Query ActorRegistry for available agents at runtime.
- Phase 2 (Planning): gpt-5-mini creates initial step-by-step plan.
- Phase 3 (Adaptive Execution): Execute each step. After each step, optionally add new steps based on results (max 2 re-plans, max 8 total steps).
- Phase 4 (Synthesis): gpt-5-mini produces final report.
- Supports PostgreSQL persistence of plans and events.

### 3.3 agents/orchestrator/ (CrewAI-based)

A separate orchestration layer using CrewAI as the execution engine:

- `orchestrator_agent.py` (1,211 lines): Main orchestrator with dynamic agent discovery, planner selection, and CrewAI crew execution.
- `llm_manager.py`: LLM quota management with model fallback chain (gpt-4o-mini -> gpt-3.5-turbo -> gpt-3.5-turbo-16k).
- `planning/`: Pluggable planner registry with deterministic and CrewAI planner implementations.
- `tools/`: Agent discovery and system evaluation tools.

---

## 4. Inter-Agent Communication

JAF implements a **hub-and-spoke communication model**:

- Agents do not communicate directly with each other.
- All communication flows through the Orchestrator (hub).
- The Orchestrator passes context (a dictionary) between steps. Each step's output is stored in the context with a key like `step_0_result`.
- For multi-agent delegation (NativeAdapter), each agent receives its sub-goal independently and returns results to the orchestrator for synthesis.

**Communication channels**:

| Channel | Mechanism | Scope |
|---------|-----------|-------|
| Step context | Dictionary passed between sequential steps | Within a single process |
| EventBus | Pub/sub broadcast of AgentAction events | In-process, all subscribers |
| Database | JSONB persistence of plan and context | Cross-process (resume support) |
| SSE stream | Server-Sent Events via FastAPI | Browser client to API server |

---

## 5. Context Management

### 5.1 Raw Context (Dict)

The Orchestrator maintains a `context: Dict[str, Any]` that is:
- Passed to `engine.execute_step(step, context)` for each step.
- Updated with step results after execution.
- Persisted as JSONB in the `processes` table.

### 5.2 TypedContext (framework/data/context.py)

A type-safe wrapper around the raw context dictionary:
- Dual storage: `_data` (typed DataEnvelope entries) and `_raw` (backward-compatible dict entries).
- Supports `set(key, contract, source_keys)` for provenance tracking.
- Implements `MutableMapping` for backward compatibility with dict operations.
- Serializable to JSON via `to_dict()`.

---

## 6. Memory Management

### 6.1 Short-Term Memory

- **Process context**: In-memory dictionary, persisted after each step. Cleared when the process completes.
- **Conversation memory**: In `agents/orchestrator/orchestrator_agent.py`, a `conversation_memory` dictionary stores prior exchanges per session. Not bounded (potential memory leak).
- **SSE event queue**: In-memory asyncio.Queue per process_id. Cleaned up after SSE stream closes.

### 6.2 Long-Term Memory

- **Process table**: Full plan and context persisted as JSONB in PostgreSQL.
- **Process events table**: Chronological audit trail of all AgentAction events.
- **LLM telemetry table**: Token usage, latency, and cost per LLM invocation.

### 6.3 Missing Memory Features

- No semantic memory or embedding-based retrieval.
- No cross-process memory sharing.
- No memory compression or summarization for long conversations.
- No TTL-based eviction for in-memory caches.

---

## 7. Resilience

| Feature | Implementation | Status |
|---------|---------------|--------|
| Step timeout | `asyncio.wait_for(timeout=step_timeout)` | Implemented |
| Retry with backoff | Exponential backoff: `delay * 2^(attempt-1)`, configurable `retry_on` exception types | Implemented |
| Process resume | Load from database, reset `executing` steps to `pending`, continue from first non-completed step | Implemented |
| State machine validation | `ProcessStateMachine` prevents invalid transitions | Implemented |
| Event bus error isolation | Subscriber errors are caught and logged without breaking the bus | Implemented |
| Database connection pooling | SQLAlchemy async pool with configurable size and overflow | Implemented |
| LLM quota management | Rate limit tracking, proactive model switching, fallback chain | Implemented (agents/orchestrator/) |
| Circuit breaker | Not implemented | Missing |
| Dead letter queue | Not implemented | Missing |

---

## 8. Observability

### 8.1 Structured Logging

- `framework/logging.py`: JSON-formatted logs with ContextVar injection.
- Context variables: `process_id`, `actor_name`, `step_id`.
- Log levels: DEBUG, INFO, WARNING, ERROR.
- Thread-safe via Python's ContextVar mechanism.

### 8.2 Event Bus

- In-process pub/sub via `EventBus` singleton.
- Payload: `AgentAction(agentId, actionType, message, status, timestamp)`.
- Built-in subscriber: `console_subscriber` (prints to stdout).
- Database subscriber: `event_bus_subscriber.db_subscriber` (persists to `process_events`).

### 8.3 Telemetry

- `TokenUsage`: Normalized token counts (prompt, completion, total).
- `TelemetryCalculator`: Cost computation based on hardcoded pricing (gpt-4o-mini: $0.00015/1K, gpt-4o: $0.00500/1K).
- `llm_telemetry` table: Persists per-invocation token usage, latency, and cost.

### 8.4 Missing Observability

- No OpenTelemetry or distributed tracing.
- No Prometheus metrics export.
- No alerting or anomaly detection.
- No dashboard integration (Grafana, Datadog).

---

## 9. Scalability

### 9.1 Current Architecture

JAF operates as a single-process application. All actors, the orchestrator, and the event bus run in the same Python process.

### 9.2 Horizontal Scalability Considerations

| Component | Scalability Path |
|-----------|-----------------|
| API layer | Multiple uvicorn workers behind a load balancer |
| Orchestrator | Requires distributed lock for process ownership; not implemented |
| Event bus | In-process only; would need Redis Pub/Sub or similar for multi-process |
| Persistence | PostgreSQL handles concurrent access; connection pooling configured |
| LLM calls | Naturally parallelizable per step (NativeEngine supports parallel_group) |

### 9.3 Vertical Scalability

- NativeEngine supports parallel step execution via `asyncio.gather()` for steps sharing the same `parallel_group`.
- CrewAIAdapter processes steps sequentially.
- NativeAdapter (jaf/) processes tool calls within a single iteration in parallel.

---

## 10. User Interface

### 10.1 Presence

| Interface Type | Present | Technology |
|----------------|---------|------------|
| Web UI | Yes | SPA (HTML/CSS/JS, no framework) |
| CLI | Yes | Typer (Python) |
| REST API | Yes | FastAPI |
| Dashboard | Partial | Process audit trail viewer in SPA |
| WebSocket | No | SSE used instead |

### 10.2 Web UI Details

- **Technology**: Vanilla HTML/CSS/JavaScript (no React, Vue, or Angular).
- **Design**: Dark-mode design system with Inter font, JetBrains Mono for code, 8px grid system.
- **Pages**: Overview, Architecture, Build Agents, Demos (with live SSE streaming), Processes (audit trail).
- **Routing**: Hash-based SPA routing (no server round-trips).
- **Streaming**: EventSource API connected to `/api/v1/stream/{process_id}`.
- **Maturity**: Functional for demonstration purposes. Not production-grade (no authentication, no error recovery on SSE disconnect).

### 10.3 REST API Access

All API endpoints are accessible without authentication (demo configuration). CORS is configured to allow all origins.

---

## 11. Maturity Assessment

| Dimension | Rating | Justification |
|-----------|--------|---------------|
| Core framework (Actor, Engine, Orchestrator) | Production-ready with caveats | Solid abstractions; thread-safety and atomicity issues need fixing |
| Persistence layer | Production-ready | Async PostgreSQL with proper repository pattern |
| Event system | Near production-ready | Functional but thread-safety bug in singleton initialization |
| Data contracts | Production-ready | Clean Pydantic v2 implementation |
| CLI | Production-ready | Simple and functional |
| REST API | Demo-grade | No authentication, no rate limiting |
| Web UI | Demo-grade | Functional for presentations; not production-grade |
| Business agents | Domain-specific | Tied to specific IT/HR systems (SOAP, REST endpoints) |
| Documentation | Partial | Architecture and API docs exist; operational runbooks missing |
