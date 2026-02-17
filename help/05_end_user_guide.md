# 05 -- End User Guide

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, commit 9cbda91

---

## 1. What JAF Does

JAF (Jems Agent Framework) is an enterprise automation framework that enables building intelligent workflows combining deterministic rules and LLM-driven reasoning. It provides:

- **Actor-based architecture**: Each business capability is encapsulated as an Actor with named tools.
- **Three execution modes**: Traditional (no LLM, free), Agentic (single LLM agent, ~$0.05), Multi-Agent (orchestrated delegation, ~$0.12).
- **Vendor independence**: Swap between CrewAI, OpenAI Responses API, or deterministic execution without changing business logic.
- **Persistence and observability**: Every process execution is persisted with full audit trail.

---

## 2. Installation

### 2.1 As a Package Dependency

```bash
pip install jaf-framework --index-url https://gitlab.jems-group.com/api/v4/projects/<PROJECT_ID>/packages/pypi/simple
```

Or in `requirements.txt`:
```
--extra-index-url https://gitlab.jems-group.com/api/v4/projects/<PROJECT_ID>/packages/pypi/simple
jaf-framework>=0.1.0
```

### 2.2 From Source

```bash
git clone https://gitlab.com/llm-ai-agents-agentic-ai/multi-agent-framework-entreprise-v2.git
cd multi-agent-framework-entreprise-v2
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-core.txt
pip install -e .
```

---

## 3. Configuration

Create a `.env` file:

```bash
# Minimal configuration
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/jaf_dev

# Required only for LLM-powered modes
OPENAI_API_KEY=sk-your-key-here
```

---

## 4. Primary Use Cases

### 4.1 Creating a Deterministic Actor

```python
from framework import Actor, ActorRegistry

class ValidationActor(Actor):
    def configure(self) -> None:
        self.name = "ValidationActor"
        self.description = "Validates input data against business rules"
        self.goal = "Ensure data integrity"
        self.tools = [self.validate_email, self.validate_amount]
        self.llm_config = None  # Deterministic -- no LLM

    def validate_email(self, email: str) -> dict:
        """Validate email format."""
        is_valid = "@" in email and "." in email.split("@")[-1]
        return {"email": email, "valid": is_valid}

    def validate_amount(self, amount: float, max_limit: float = 10000.0) -> dict:
        """Validate transaction amount against limit."""
        return {"amount": amount, "approved": amount <= max_limit}

ActorRegistry.register("ValidationActor", ValidationActor)
actor = ActorRegistry.get("ValidationActor")
result = actor.validate_email("user@example.com")
```

### 4.2 Running a Deterministic Workflow

```python
import asyncio
from framework import NativeEngine, Orchestrator, Plan, PlanStep

plan = Plan(
    steps=[
        PlanStep(
            actor_name="ValidationActor",
            tool_name="validate_email",
            parameters={"email": "user@example.com"},
        ),
        PlanStep(
            actor_name="ValidationActor",
            tool_name="validate_amount",
            parameters={"amount": 5000.0},
        ),
    ],
    status="PLANNING",
)

engine = NativeEngine(default_plan=plan)

async def run():
    orchestrator = Orchestrator(engine=engine, session_maker=None)
    result = await orchestrator.run(
        goal="Validate user data",
        actors=[ActorRegistry.get("ValidationActor")],
        context={},
    )
    return result

asyncio.run(run())
```

### 4.3 Using the EventBus for Real-Time Updates

```python
from framework import get_event_bus, AgentAction

bus = get_event_bus()

def my_handler(action):
    print(f"[{action.agentId}] {action.actionType}: {action.message}")

bus.subscribe(my_handler)

bus.emit(AgentAction(
    agentId="ValidationActor",
    actionType="validation_complete",
    message="Email validated successfully",
    status="complete",
))
```

### 4.4 Scaffolding a New Project

```bash
pip install -e .
jaf new my_automation_project
```

This creates:
```
my_automation_project/
├── my_actors/
│   ├── __init__.py
│   └── sample_actor.py
├── workflows/
│   ├── __init__.py
│   └── sample_workflow.py
├── tests/
│   ├── __init__.py
│   └── test_sample_actor.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 5. Known Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| No built-in authentication on REST API | API endpoints are open | Deploy behind a reverse proxy with authentication |
| EventBus is in-process only | Events do not propagate across processes or hosts | Use database event subscriber for persistence |
| VertexAI adapter is deprecated | Cannot use Google Vertex AI engine | Use CrewAIAdapter or NativeEngine |
| LLM pricing is hardcoded | Cost estimates may be inaccurate | Update `framework/observability/telemetry.py` manually |
| No distributed execution | All steps execute in a single process | Acceptable for current scale; future Celery integration planned |
| CrewAI dependency | Breaking changes in CrewAI may affect agentic flows | Pin CrewAI version; test before upgrading |

---

## 6. Technical FAQ

**Q: Can I use JAF without an LLM API key?**
A: Yes. Set `llm_config = None` on all actors and use `NativeEngine`. The Traditional execution mode requires no LLM and incurs no cost.

**Q: Can I use JAF without PostgreSQL?**
A: For unit tests and basic development, set `DATABASE_URL=sqlite+aiosqlite:///./test.db`. For production use with process persistence and audit trails, PostgreSQL is required.

**Q: How do I add a new execution engine?**
A: Subclass `EngineAbstraction` and implement the three abstract methods: `generate_plan()`, `execute_step()`, `evaluate_progress()`. Register the engine in `EngineFactory` or pass it directly to the Orchestrator.

**Q: How do I run the CEO demo?**
A: Install full dependencies (`pip install -r requirements.txt`), set `DATABASE_URL` and `OPENAI_API_KEY`, run `uvicorn jaf.api.main:app --reload --port 8000`, and open `http://localhost:8000/` in a browser. Navigate to the Demos page to run scenarios.

**Q: How do I monitor process execution?**
A: Subscribe to the EventBus for real-time in-process events. For persistent audit trails, query the `process_events` table via the REST API at `/api/v1/processes/{id}/events`.

**Q: What models does JAF support?**
A: Any model compatible with the OpenAI API (via `openai` package) or CrewAI (via `crewai` package). The default model is configured via the `DEFAULT_MODEL` environment variable (default: `gpt-4o-mini`). Per-actor model selection is supported via `LLMConfig(model="model-name")`.
