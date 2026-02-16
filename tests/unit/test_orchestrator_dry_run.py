import asyncio

from framework.orchestrator import Orchestrator
from framework.actor.registry import ActorRegistry
from framework.engine.engine_abstraction import EngineAbstraction
from framework.types import Plan, PlanStep
from examples.simple_actor_example import CalculatorActor

# ============================================================
# MOCK ENGINE
# ============================================================


class MockEngine(EngineAbstraction):
    def __init__(self, plan: Plan):
        self.plan = plan
        self.execute_called = False

    async def generate_plan(self, goal, available_actors):
        return self.plan

    async def execute_step(self, step, context):
        self.execute_called = True
        raise RuntimeError("execute_step must NOT be called in dry_run mode")

    async def evaluate_progress(self, plan, result):
        pass


# ============================================================
# UTILS
# ============================================================


def setup_registry():
    ActorRegistry.clear()
    ActorRegistry.register("CalculatorActor", CalculatorActor)


async def run_dry_run(plan: Plan):
    setup_registry()
    engine = MockEngine(plan)
    orchestrator = Orchestrator(engine=engine, session_maker=lambda: None)

    result = await orchestrator.run(
        goal="test dry run", actors=[CalculatorActor], dry_run=True
    )

    return result, engine


# ============================================================
# TESTS
# ============================================================


def test_dry_run_happy_path():
    """
    ✔ dry_run parameter
    ✔ valid actor
    ✔ valid tool
    ✔ simulated ProcessResult
    ✔ no side effects
    """
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 2, "b": 3},
            )
        ]
    )

    result, engine = asyncio.run(run_dry_run(plan))

    assert result.dry_run is True
    assert result.status.name == "DRY_RUN"
    assert result.plan is not None
    assert result.validation_report is not None
    assert engine.execute_called is False


def test_dry_run_missing_actor():
    """
    ✔ validates actor existence
    """
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="UnknownActor", tool_name="add", parameters={"a": 1, "b": 2}
            )
        ]
    )

    result, _ = asyncio.run(run_dry_run(plan))

    errors = [
        issue for issue in result.validation_report.issues if issue.level == "error"
    ]

    assert any("UnknownActor" in issue.message for issue in errors)


def test_dry_run_missing_tool():
    """
    ✔ validates tool existence on actor
    """
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 2, "b": 3},
            )
        ]
    )

    result, _ = asyncio.run(run_dry_run(plan))

    errors = [
        issue for issue in result.validation_report.issues if issue.level == "error"
    ]

    assert any("multiply" in issue.message for issue in errors)


def test_dry_run_invalid_parameter_payload():
    """
    ✔ validates parameter payload (structure-level)
    NOTE:
    Strict type validation is not implemented yet.
    This test ensures the dry-run remains stable with invalid inputs.
    """
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": "2", "b": 3},  # invalid type but allowed for now
            )
        ]
    )

    result, engine = asyncio.run(run_dry_run(plan))

    # dry-run must not crash
    assert result.dry_run is True
    assert result.validation_report is not None
    assert engine.execute_called is False


def test_dry_run_no_side_effects():
    """
    ✔ ensures no tool execution occurs in dry_run
    """
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 10, "b": 5},
            )
        ]
    )

    result, engine = asyncio.run(run_dry_run(plan))

    assert engine.execute_called is False
    assert result.status.name == "DRY_RUN"
