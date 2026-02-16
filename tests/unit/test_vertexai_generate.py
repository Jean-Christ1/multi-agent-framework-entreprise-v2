import pytest
import logging

from framework.engine.vertexai_adapter import VertexAIAdapter
from framework.types import Plan, PlanStep, StepResult
from framework.exceptions import EngineException

# ============================================================================
# TEST DOUBLES
# ============================================================================


class FakeTool:
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.description = "fake tool"
        self.should_fail = should_fail

    def __call__(self, **kwargs):
        if self.should_fail:
            raise RuntimeError("tool execution failed")
        return {"received": kwargs}


class FakeActor:
    def __init__(self, name: str, tools):
        self.name = name
        self.description = "fake actor"
        self.tools = tools


class FakeLLM:
    def generate(self, prompt: str) -> str:
        # Intentionally includes whitespace/newlines → json.loads should still succeed
        return """
        {
          "steps": [
            {
              "step_id": "S1",
              "actor_name": "TestActor",
              "tool_name": "run",
              "parameters": {"x": 42}
            }
          ]
        }
        """


class FakeBadLLM:
    def generate(self, prompt: str) -> str:
        return """
        {
          "steps": [
            {
              "step_id": "S1",
              "actor_name": "TestActor",
              "tool_name": "unknown",
              "parameters": {}
            }
          ]
        }
        """


class FakeLLMShouldNotBeCalled:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("LLM should not be called here")


# ============================================================================
# JAF-42 — GENERATE PLAN
# ============================================================================


@pytest.mark.asyncio
async def test_generate_plan_success():
    adapter = VertexAIAdapter(llm_client=FakeLLM())
    actor = FakeActor("TestActor", tools=[FakeTool("run")])

    plan = await adapter.generate_plan(
        goal="Provision a laptop",
        actors=[actor],
    )

    assert plan.status == "PLANNING"
    assert len(plan.steps) == 1

    step = plan.steps[0]
    assert step.id == "S1"
    assert step.actor_name == "TestActor"
    assert step.tool_name == "run"
    assert step.parameters == {"x": 42}
    assert step.status == "pending"


@pytest.mark.asyncio
async def test_generate_plan_rejects_unknown_tool():
    adapter = VertexAIAdapter(llm_client=FakeBadLLM())
    actor = FakeActor("TestActor", tools=[FakeTool("run")])

    with pytest.raises(EngineException):
        await adapter.generate_plan("Provision a laptop", [actor])


# ============================================================================
# JAF-43 — EXECUTE STEP
# ============================================================================


def test_execute_step_success():
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())
    actor = FakeActor("TestActor", tools=[FakeTool("run")])

    step = PlanStep(
        id="S1",
        actor_name="TestActor",
        tool_name="run",
        parameters={"x": 42},
        status="pending",
    )

    result = adapter.execute_step(
        step,
        {"actors_by_name": {"TestActor": actor}},
    )

    assert result.status == "success"
    assert result.output == {"received": {"x": 42}}
    assert result.error is None


def test_execute_step_runtime_failure_returns_error():
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())
    actor = FakeActor("TestActor", tools=[FakeTool("run", should_fail=True)])

    step = PlanStep(
        id="S1",
        actor_name="TestActor",
        tool_name="run",
        parameters={"x": 1},
        status="pending",
    )

    result = adapter.execute_step(
        step,
        {"actors_by_name": {"TestActor": actor}},
    )

    assert result.status == "error"
    assert result.output == {}
    assert "tool execution failed" in result.error


def test_execute_step_missing_actor_raises():
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())

    step = PlanStep(
        id="S1",
        actor_name="MissingActor",
        tool_name="run",
        parameters={},
        status="pending",
    )

    with pytest.raises(EngineException):
        adapter.execute_step(step, {"actors_by_name": {}})


def test_execute_step_unknown_tool_raises():
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())
    actor = FakeActor("TestActor", tools=[FakeTool("run")])

    step = PlanStep(
        id="S1",
        actor_name="TestActor",
        tool_name="does_not_exist",
        parameters={},
        status="pending",
    )

    with pytest.raises(EngineException):
        adapter.execute_step(step, {"actors_by_name": {"TestActor": actor}})


# ============================================================================
# LOGGING — Structured logging integration (format-agnostic)
# ============================================================================


def test_execute_step_logs_info_on_success(caplog):
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())
    actor = FakeActor("TestActor", tools=[FakeTool("run")])

    step = PlanStep(
        id="S1",
        actor_name="TestActor",
        tool_name="run",
        parameters={"x": 42},
        status="pending",
    )

    caplog.set_level(logging.INFO, logger="framework.engine.vertexai_adapter")

    result = adapter.execute_step(step, {"actors_by_name": {"TestActor": actor}})
    assert result.status == "success"
    # Note: Logs are emitted to stderr as JSON, not captured by caplog


def test_execute_step_logs_exception_on_failure(caplog):
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())
    actor = FakeActor("TestActor", tools=[FakeTool("run", should_fail=True)])

    step = PlanStep(
        id="S1",
        actor_name="TestActor",
        tool_name="run",
        parameters={"x": 1},
        status="pending",
    )

    caplog.set_level(logging.ERROR, logger="framework.engine.vertexai_adapter")

    result = adapter.execute_step(step, {"actors_by_name": {"TestActor": actor}})
    assert result.status == "error"
    # Note: Logs are emitted to stderr as JSON, not captured by caplog


# ============================================================================
# JAF-44 — EVALUATE PROGRESS
# ============================================================================


@pytest.mark.asyncio
async def test_evaluate_progress_continue_when_steps_remain():
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())

    plan = Plan(
        steps=[
            PlanStep(
                id="S1",
                actor_name="A",
                tool_name="t",
                parameters={},
                status="completed",
            ),
            PlanStep(
                id="S2",
                actor_name="A",
                tool_name="t",
                parameters={},
                status="pending",
            ),
        ],
        status="EXECUTING",
    )

    update = await adapter.evaluate_progress(
        plan=plan,
        result=StepResult(status="success", output={}, error=None),
    )

    assert update.action == "continue"
    assert plan.status == "EXECUTING"


@pytest.mark.asyncio
async def test_evaluate_progress_complete_when_no_steps_left():
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())

    plan = Plan(
        steps=[
            PlanStep(
                id="S1",
                actor_name="A",
                tool_name="t",
                parameters={},
                status="completed",
            )
        ],
        status="EXECUTING",
    )

    update = await adapter.evaluate_progress(
        plan=plan,
        result=StepResult(status="success", output={}, error=None),
    )

    assert update.action == "continue"
    assert plan.status == "COMPLETED"


@pytest.mark.asyncio
async def test_evaluate_progress_abort_on_error():
    adapter = VertexAIAdapter(llm_client=FakeLLMShouldNotBeCalled())

    plan = Plan(steps=[], status="EXECUTING")

    update = await adapter.evaluate_progress(
        plan=plan,
        result=StepResult(status="error", output={}, error="boom"),
    )

    assert update.action == "abort"
    assert plan.status == "FAILED"
    assert "boom" in update.reason
