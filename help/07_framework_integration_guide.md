# 07 -- Framework Integration Guide

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, tag v1.4.2, commit 9cbda91

---

## 1. Recommended Version

**Tag**: `v1.4.2`
**Branch**: `main`
**Commit**: 9cbda912b63e46890ded381645e80b10a7575cf2

**Justification**: v1.4.2 is the latest semantic version tag. All tags in this repository resolve to the same commit, so v1.4.2 represents the complete, current state of the framework. Using the latest tag communicates to downstream consumers that they are on the most recent stable baseline.

**Risk of alternative tags**: No functional risk (identical code), but using an older tag creates misleading dependency metadata in downstream `requirements.txt` or lock files.

---

## 2. Dependencies

### 2.1 Minimum Dependencies (Deterministic Mode Only)

```txt
jaf-framework>=0.1.0
# or install directly:
pydantic>=2.0,<3.0
pydantic-settings>=2.0,<3.0
sqlalchemy>=2.0,<3.0
asyncpg>=0.28,<1.0
aiosqlite>=0.19,<1.0
python-dotenv>=1.0,<2.0
```

### 2.2 With LLM Support

```txt
jaf-framework>=0.1.0
crewai>=0.28,<1.0
openai>=1.0,<2.0
```

### 2.3 With API Server

```txt
jaf-framework>=0.1.0
fastapi>=0.100,<1.0
uvicorn[standard]>=0.23,<1.0
httpx>=0.25,<1.0
```

---

## 3. Minimal Configuration

### 3.1 Environment Variables

```bash
# Required for persistence
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/my_project_db

# Required for LLM operations (skip for deterministic-only)
OPENAI_API_KEY=sk-your-key-here

# Optional
DEFAULT_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.0
LOG_LEVEL=INFO
```

### 3.2 Database Setup

```bash
createdb my_project_db
psql my_project_db < migrations/001_create_processes.sql
psql my_project_db < migrations/002_create_llm_telemetry.sql
psql my_project_db < migrations/003_create_process_events.sql
```

---

## 4. Integration Example: Data Platform Migration SaaS

### 4.1 Context

Integration into a SaaS platform for managing data platform migrations. The system must:

- **Agent 1 (DocumentAnalyzer)**: Parse migration documentation and extract source/target platform details.
- **Agent 2 (PatternExtractor)**: Identify technical patterns (ETL jobs, data models, dependencies) from source platform metadata.
- **Agent 3 (MigrationPlanner)**: Generate a step-by-step migration plan with risk assessment.
- **Orchestrator**: Coordinate the three agents in sequence, passing context between steps.

### 4.2 Actor Definitions

```python
# migration_actors.py
from framework import Actor, ActorRegistry, LLMConfig


class DocumentAnalyzerActor(Actor):
    """Analyzes migration documentation."""

    def configure(self) -> None:
        self.name = "DocumentAnalyzer"
        self.description = "Parses migration documents and extracts platform details"
        self.goal = "Extract source and target platform specifications from documentation"
        self.tools = [self.parse_document, self.extract_platforms]
        self.llm_config = LLMConfig(model="gpt-4o-mini", temperature=0.0)

    def parse_document(self, document_path: str) -> dict:
        """Parse a migration specification document."""
        # Implementation: read and parse the document
        return {
            "title": "Oracle to Snowflake Migration",
            "source_platform": "Oracle 19c",
            "target_platform": "Snowflake Enterprise",
            "tables_count": 245,
            "estimated_data_volume_gb": 1200,
        }

    def extract_platforms(self, parsed_doc: dict) -> dict:
        """Extract source and target platform capabilities."""
        return {
            "source": {
                "platform": parsed_doc["source_platform"],
                "supports_cdc": True,
                "has_stored_procedures": True,
            },
            "target": {
                "platform": parsed_doc["target_platform"],
                "supports_semi_structured": True,
                "has_streams": True,
            },
        }


class PatternExtractorActor(Actor):
    """Identifies technical patterns from source platform metadata."""

    def configure(self) -> None:
        self.name = "PatternExtractor"
        self.description = "Extracts ETL patterns, data models, and dependencies"
        self.goal = "Catalog all technical patterns requiring migration attention"
        self.tools = [self.analyze_etl_jobs, self.map_dependencies]
        self.llm_config = LLMConfig(model="gpt-4o-mini", temperature=0.0)

    def analyze_etl_jobs(self, source_platform: str, tables_count: int) -> dict:
        """Analyze ETL job patterns from source platform."""
        return {
            "total_jobs": 87,
            "job_types": {
                "batch_load": 45,
                "incremental_cdc": 22,
                "stored_procedure": 15,
                "manual_export": 5,
            },
            "complexity_distribution": {
                "simple": 52,
                "medium": 25,
                "complex": 10,
            },
        }

    def map_dependencies(self, etl_analysis: dict) -> dict:
        """Map inter-table and inter-job dependencies."""
        return {
            "dependency_chains": 12,
            "critical_path_length": 5,
            "circular_dependencies": 0,
            "external_system_dependencies": ["SAP ERP", "Salesforce CRM"],
        }


class MigrationPlannerActor(Actor):
    """Generates migration plan with risk assessment."""

    def configure(self) -> None:
        self.name = "MigrationPlanner"
        self.description = "Creates phased migration plan with risk analysis"
        self.goal = "Produce an actionable migration plan with timeline and risks"
        self.tools = [self.generate_plan, self.assess_risks]
        self.llm_config = LLMConfig(model="gpt-4o-mini", temperature=0.0)

    def generate_plan(self, patterns: dict, dependencies: dict) -> dict:
        """Generate phased migration plan."""
        return {
            "phases": [
                {
                    "name": "Phase 1: Schema Migration",
                    "duration_weeks": 3,
                    "tables": 245,
                    "approach": "automated DDL conversion",
                },
                {
                    "name": "Phase 2: Simple ETL Migration",
                    "duration_weeks": 4,
                    "jobs": 52,
                    "approach": "direct translation to Snowflake tasks",
                },
                {
                    "name": "Phase 3: Complex ETL Migration",
                    "duration_weeks": 6,
                    "jobs": 35,
                    "approach": "manual re-engineering with validation",
                },
                {
                    "name": "Phase 4: Validation and Cutover",
                    "duration_weeks": 2,
                    "approach": "parallel run with data reconciliation",
                },
            ],
            "total_duration_weeks": 15,
        }

    def assess_risks(self, plan: dict) -> dict:
        """Assess migration risks."""
        return {
            "risks": [
                {
                    "risk": "Stored procedure incompatibility",
                    "severity": "high",
                    "mitigation": "Early proof-of-concept for complex procedures",
                },
                {
                    "risk": "Data volume transfer time",
                    "severity": "medium",
                    "mitigation": "Use Snowflake COPY with parallel loading",
                },
            ],
            "overall_risk_level": "medium",
        }


# Register all actors
ActorRegistry.register("DocumentAnalyzer", DocumentAnalyzerActor)
ActorRegistry.register("PatternExtractor", PatternExtractorActor)
ActorRegistry.register("MigrationPlanner", MigrationPlannerActor)
```

### 4.3 Workflow Execution

```python
# run_migration_analysis.py
import asyncio
from framework import (
    Orchestrator,
    Plan,
    PlanStep,
    NativeEngine,
    ActorRegistry,
    get_event_bus,
    AgentAction,
)
from framework.persistence.database import async_session_maker

# Import actor definitions (registers them)
import migration_actors  # noqa: F401


def log_event(action: AgentAction) -> None:
    """Event handler for logging."""
    print(f"[{action.agentId}] {action.actionType}: {action.message}")


async def run_migration_analysis():
    # Subscribe to events for logging
    bus = get_event_bus()
    bus.subscribe(log_event)

    # Retrieve registered actors
    doc_actor = ActorRegistry.get("DocumentAnalyzer")
    pattern_actor = ActorRegistry.get("PatternExtractor")
    planner_actor = ActorRegistry.get("MigrationPlanner")

    # Define execution plan
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="DocumentAnalyzer",
                tool_name="parse_document",
                parameters={"document_path": "/data/migration_spec.pdf"},
            ),
            PlanStep(
                actor_name="DocumentAnalyzer",
                tool_name="extract_platforms",
                parameters={"parsed_doc": "${step_0_result}"},
            ),
            PlanStep(
                actor_name="PatternExtractor",
                tool_name="analyze_etl_jobs",
                parameters={
                    "source_platform": "Oracle 19c",
                    "tables_count": 245,
                },
            ),
            PlanStep(
                actor_name="PatternExtractor",
                tool_name="map_dependencies",
                parameters={"etl_analysis": "${step_2_result}"},
            ),
            PlanStep(
                actor_name="MigrationPlanner",
                tool_name="generate_plan",
                parameters={
                    "patterns": "${step_2_result}",
                    "dependencies": "${step_3_result}",
                },
            ),
            PlanStep(
                actor_name="MigrationPlanner",
                tool_name="assess_risks",
                parameters={"plan": "${step_4_result}"},
            ),
        ],
        status="PLANNING",
    )

    # Create engine with pre-built plan
    engine = NativeEngine(default_plan=plan)

    # Create orchestrator
    orchestrator = Orchestrator(
        engine=engine,
        session_maker=async_session_maker,
        step_timeout=120,
        max_retries=2,
        retry_delay=5.0,
        retry_on=(ConnectionError, TimeoutError),
    )

    # Execute
    result = await orchestrator.run(
        goal="Analyze Oracle-to-Snowflake migration and produce a phased plan",
        actors=[doc_actor, pattern_actor, planner_actor],
        context={"project": "oracle-to-snowflake-2026"},
    )

    print(f"\nProcess {result.process_id} completed: {result.status.value}")
    return result


if __name__ == "__main__":
    asyncio.run(run_migration_analysis())
```

### 4.4 Execution Flow

```
1. Orchestrator creates process (PENDING) in database
2. NativeEngine returns pre-built plan (6 steps)
3. Step 0: DocumentAnalyzer.parse_document() --> parsed document dict
4. Step 1: DocumentAnalyzer.extract_platforms() --> platform capabilities
5. Step 2: PatternExtractor.analyze_etl_jobs() --> ETL job analysis
6. Step 3: PatternExtractor.map_dependencies() --> dependency map
7. Step 4: MigrationPlanner.generate_plan() --> 4-phase migration plan
8. Step 5: MigrationPlanner.assess_risks() --> risk assessment
9. Orchestrator marks process as COMPLETED
10. All events persisted to process_events table
```

### 4.5 Error Handling

```python
from framework.exceptions import FrameworkException, EngineException

try:
    result = await orchestrator.run(goal=goal, actors=actors, context=context)
except EngineException as e:
    # Engine-level failure (LLM error, plan generation failure)
    logger.error(f"Engine error: {e}")
except FrameworkException as e:
    # Framework-level failure (persistence, state machine)
    logger.error(f"Framework error: {e}")
except Exception as e:
    # Unexpected error
    logger.critical(f"Unexpected error: {e}", exc_info=True)
```

### 4.6 Logging Configuration

```python
import logging
from framework.logging import get_logger, set_logging_context

logger = get_logger("migration_analysis")

# Set context for structured logging
set_logging_context(process_id="proc-123", actor_name="DocumentAnalyzer")

# Logs will include process_id and actor_name as JSON fields
logger.info("Starting document analysis")
```

---

## 5. Production Best Practices

### 5.1 Environment Isolation

- Use separate `.env` files per environment (development, staging, production).
- Never commit `.env` files to version control.
- Use a secrets manager for API keys in production.

### 5.2 Database Management

- Apply migrations in order during deployment.
- Use connection pooling (DB_POOL_SIZE, DB_MAX_OVERFLOW).
- Monitor the `processes` table for growth; implement archival strategy for completed processes.

### 5.3 LLM Cost Control

- Use `LLMConfig(temperature=0.0)` for deterministic outputs when reasoning variation is unnecessary.
- Prefer `gpt-4o-mini` over `gpt-4o` for cost-sensitive operations.
- Monitor the `llm_telemetry` table for cost tracking.
- Set `LLM_MAX_RPM` to prevent rate limit exhaustion.

### 5.4 Error Recovery

- Always configure `retry_on` with the specific exception types relevant to your integration (e.g., network errors for external API actors).
- Set `step_timeout` based on the slowest expected tool execution time plus a safety margin.
- Use `Orchestrator.resume(process_id)` for recovering interrupted processes after service restart.

### 5.5 Monitoring

- Subscribe a custom EventBus handler that forwards events to your monitoring system (Datadog, Prometheus, ELK).
- Query the `process_events` table for audit trail analysis.
- Track process duration via `created_at` and `updated_at` timestamps on the `processes` table.
