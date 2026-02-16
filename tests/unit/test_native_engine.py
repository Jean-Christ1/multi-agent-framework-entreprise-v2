import pytest

from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry
from framework.engine.native_engine import NativeEngine
from framework.types import Plan, PlanStep, StepResult

# ---------------------------------------------------------------------------
# Helpers: Mock Actors
# ---------------------------------------------------------------------------


class SyncActor(Actor):
    def configure(self) -> None:
        self.name = "SyncActor"
        self.description = "Actor with sync tools"
        self.goal = "Testing sync tools"
        self.llm_config = None
        self.tools = [self.add, self.echo_default, self.returns_dict]
        self.utilities = []

    def add(self, a: int, b: int) -> int:
        """Return a + b"""
        return a + b

    def echo_default(self, msg: str = "hello") -> str:
        """Return msg (default provided)"""
        return msg

    def returns_dict(self) -> dict:
        """Return a dict directly"""
        return {"ok": True, "value": 123}


class AsyncActor(Actor):
    def configure(self) -> None:
        self.name = "AsyncActor"
        self.description = "Actor with async tools"
        self.goal = "Testing async tools"
        self.llm_config = None
        self.tools = [self.async_mul]
        self.utilities = []

    async def async_mul(self, x: int, y: int) -> int:
        """Return x * y (async)"""
        return x * y


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_registry():
    """
    Ensure registry is clean between tests (important because ActorRegistry is singleton).
    """
    ActorRegistry.clear()
    yield
    ActorRegistry.clear()


@pytest.fixture
def registered_actors():
    ActorRegistry.register("SyncActor", SyncActor)
    ActorRegistry.register("AsyncActor", AsyncActor)
    return ["SyncActor", "AsyncActor"]


# ---------------------------------------------------------------------------
# Tests: generate_plan()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_plan_with_preset_plan(registered_actors):
    engine = NativeEngine()

    preset = Plan(
        steps=[
            PlanStep(
                actor_name="SyncActor",
                tool_name="add",
                parameters={"a": 1, "b": 2},
                status="pending",
            )
        ],
        status="PLANNING",
    )
    engine.set_plan(preset)

    actors = [ActorRegistry.get("SyncActor")]
    plan = await engine.generate_plan("any goal", actors)

    assert plan is preset
    assert len(plan.steps) == 1
    assert plan.steps[0].actor_name == "SyncActor"
    assert plan.steps[0].tool_name == "add"


@pytest.mark.asyncio
async def test_generate_plan_with_custom_plan_builder(registered_actors):
    engine = NativeEngine()

    def builder(goal: str, actors: list[Actor]) -> Plan:
        # Create a single-step plan regardless of tools
        return Plan(
            steps=[
                PlanStep(
                    actor_name=actors[0].name,
                    tool_name=actors[0].tools[0].__name__,
                    parameters={"a": 10, "b": 20},
                    status="pending",
                )
            ],
            status="PLANNING",
        )

    engine.set_plan_builder(builder)

    actors = [ActorRegistry.get("SyncActor")]
    plan = await engine.generate_plan("sum something", actors)

    assert len(plan.steps) == 1
    assert plan.steps[0].actor_name == "SyncActor"
    assert plan.steps[0].tool_name == "add"
    assert plan.steps[0].parameters == {"a": 10, "b": 20}


@pytest.mark.asyncio
async def test_generate_plan_sequential_fallback_includes_all_tools(registered_actors):
    engine = NativeEngine()

    actors = [ActorRegistry.get("SyncActor"), ActorRegistry.get("AsyncActor")]
    plan = await engine.generate_plan("fallback plan", actors)

    # SyncActor has 3 tools, AsyncActor has 1 tool => total 4 steps
    assert len(plan.steps) == 4
    assert plan.status == "PLANNING"

    # Ensure ordering: all SyncActor tools then AsyncActor tools
    assert plan.steps[0].actor_name == "SyncActor"
    assert plan.steps[1].actor_name == "SyncActor"
    assert plan.steps[2].actor_name == "SyncActor"
    assert plan.steps[3].actor_name == "AsyncActor"

    assert plan.steps[0].tool_name == "add"
    assert plan.steps[1].tool_name == "echo_default"
    assert plan.steps[2].tool_name == "returns_dict"
    assert plan.steps[3].tool_name == "async_mul"

    # Parameter inference checks
    # add(a,b) has no defaults => placeholders
    assert plan.steps[0].parameters["a"] == "{context.a}"
    assert plan.steps[0].parameters["b"] == "{context.b}"

    # echo_default(msg="hello") => default
    assert plan.steps[1].parameters["msg"] == "hello"

    # returns_dict() => no params
    assert plan.steps[2].parameters == {}

    # async_mul(x,y) => placeholders
    assert plan.steps[3].parameters["x"] == "{context.x}"
    assert plan.steps[3].parameters["y"] == "{context.y}"


# ---------------------------------------------------------------------------
# Tests: execute_step()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_step_direct_tool_invocation_sync(registered_actors):
    engine = NativeEngine()

    step = PlanStep(
        actor_name="SyncActor",
        tool_name="add",
        parameters={"a": 2, "b": 3},
        status="pending",
    )

    result = await engine.execute_step(step, context={})

    assert isinstance(result, StepResult)
    assert result.status == "success"
    assert result.error is None
    assert result.output == {"result": 5}
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_execute_step_with_async_tools(registered_actors):
    engine = NativeEngine()

    step = PlanStep(
        actor_name="AsyncActor",
        tool_name="async_mul",
        parameters={"x": 6, "y": 7},
        status="pending",
    )

    result = await engine.execute_step(step, context={})

    assert result.status == "success"
    assert result.output == {"result": 42}


@pytest.mark.asyncio
async def test_execute_step_parameter_resolution_from_context(registered_actors):
    engine = NativeEngine()

    # a comes from context, b is fixed
    step = PlanStep(
        actor_name="SyncActor",
        tool_name="add",
        parameters={"a": "{context.a}", "b": 10},
        status="pending",
    )

    result = await engine.execute_step(step, context={"a": 5})

    assert result.status == "success"
    assert result.output == {"result": 15}


@pytest.mark.asyncio
async def test_execute_step_returns_dict_passthrough(registered_actors):
    engine = NativeEngine()

    step = PlanStep(
        actor_name="SyncActor",
        tool_name="returns_dict",
        parameters={},
        status="pending",
    )

    result = await engine.execute_step(step, context={})

    assert result.status == "success"
    # if tool returns dict, engine returns it as-is (not wrapped in {"result": ...})
    assert result.output == {"ok": True, "value": 123}


@pytest.mark.asyncio
async def test_execute_step_tool_not_found_returns_error(registered_actors):
    engine = NativeEngine()

    step = PlanStep(
        actor_name="SyncActor",
        tool_name="does_not_exist",
        parameters={},
        status="pending",
    )

    result = await engine.execute_step(step, context={})

    assert result.status == "error"
    assert "not found" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# Tests: _resolve_parameters() (covered via execute_step above, but also direct)
# ---------------------------------------------------------------------------


def test_parameter_resolution_helper_direct(registered_actors):
    engine = NativeEngine()

    params = {"x": "{context.x}", "y": 2, "z": "{context.missing}"}
    context = {"x": 10}

    resolved = engine._resolve_parameters(params, context)  # ok to test helper

    assert resolved["x"] == 10
    assert resolved["y"] == 2
    # missing context keys keep placeholder
    assert resolved["z"] == "{context.missing}"


# ---------------------------------------------------------------------------
# Tests: evaluate_progress()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_progress_plan_already_completed(registered_actors):
    engine = NativeEngine()

    plan = Plan(steps=[], status="COMPLETED")
    result = StepResult(output={}, status="success")

    update = await engine.evaluate_progress(plan, result)

    assert update.action == "continue"
    assert "already completed" in update.reason.lower()


@pytest.mark.asyncio
async def test_evaluate_progress_plan_failed_state_aborts(registered_actors):
    engine = NativeEngine()

    plan = Plan(steps=[], status="FAILED")
    result = StepResult(output={}, status="success")

    update = await engine.evaluate_progress(plan, result)

    assert update.action == "abort"
    assert "failed state" in update.reason.lower()


@pytest.mark.asyncio
async def test_evaluate_progress_step_error_aborts(registered_actors):
    engine = NativeEngine()

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="SyncActor",
                tool_name="add",
                parameters={"a": 1, "b": 2},
                status="pending",
            )
        ],
        status="EXECUTING",
    )
    result = StepResult(output={}, status="error", error="boom")

    update = await engine.evaluate_progress(plan, result)

    assert update.action == "abort"
    assert "step failed" in update.reason.lower()
    assert "boom" in update.reason


@pytest.mark.asyncio
async def test_evaluate_progress_all_steps_completed_continues(registered_actors):
    engine = NativeEngine()

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="SyncActor",
                tool_name="add",
                parameters={"a": 1, "b": 2},
                status="completed",
            )
        ],
        status="EXECUTING",
    )
    result = StepResult(output={"result": 3}, status="success")

    update = await engine.evaluate_progress(plan, result)

    assert update.action == "continue"
    assert "all steps completed" in update.reason.lower()


@pytest.mark.asyncio
async def test_evaluate_progress_more_pending_steps_continues(registered_actors):
    engine = NativeEngine()

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="SyncActor",
                tool_name="add",
                parameters={"a": 1, "b": 2},
                status="completed",
            ),
            PlanStep(
                actor_name="SyncActor",
                tool_name="echo_default",
                parameters={"msg": "x"},
                status="pending",
            ),
        ],
        status="EXECUTING",
    )
    result = StepResult(output={"result": 3}, status="success")

    update = await engine.evaluate_progress(plan, result)

    assert update.action == "continue"
    assert "continuing to next step" in update.reason.lower()
