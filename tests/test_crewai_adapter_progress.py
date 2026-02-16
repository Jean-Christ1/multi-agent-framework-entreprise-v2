import pytest
from unittest.mock import patch

from framework.types import Plan, PlanStep, StepResult
from framework.engine.crewai_adapter import CrewAIAdapter


@pytest.fixture
def adapter():
    return CrewAIAdapter(llm_client=None)


@pytest.fixture
def sample_plan():
    step1 = PlanStep(
        actor_name="DevOps", tool_name="provision", parameters={}, status="completed"
    )
    step2 = PlanStep(
        actor_name="DevOps", tool_name="configure", parameters={}, status="pending"
    )

    return Plan(steps=[step1, step2], status="PLANNING")


@pytest.mark.asyncio
async def test_evaluate_progress_continue(adapter, sample_plan):
    result = StepResult(output={"status": "ok"}, status="success", execution_time=100)

    update = await adapter.evaluate_progress(sample_plan, result)

    assert update.action == "continue"
    assert "moving to next step" in update.reason


@pytest.mark.asyncio
async def test_evaluate_progress_error_abort(adapter, sample_plan):
    result = StepResult(
        output={}, status="error", error="Timeout connection to AWS", execution_time=50
    )

    update = await adapter.evaluate_progress(sample_plan, result)

    assert update.action == "abort"
    assert "Step execution failed" in update.reason
    assert "Timeout connection" in update.reason


@pytest.mark.asyncio
async def test_evaluate_progress_empty_output_modify(adapter, sample_plan):
    result = StepResult(output={}, status="success", execution_time=10)  # Gol

    update = await adapter.evaluate_progress(sample_plan, result)

    assert update.action == "modify"
    assert "no output" in update.reason


@pytest.mark.asyncio
async def test_evaluate_progress_all_completed(adapter):
    step = PlanStep(
        actor_name="DevOps", tool_name="cleanup", parameters={}, status="completed"
    )
    plan = Plan(steps=[step], status="PLANNING")

    with patch.object(Plan, "next_step", return_value=None):
        result = StepResult(output={"done": True}, status="success")
        update = await adapter.evaluate_progress(plan, result)

        assert update.action == "continue"
        assert "All steps completed" in update.reason


@pytest.mark.asyncio
async def test_evaluate_progress_already_failed(adapter, sample_plan):
    sample_plan.status = "FAILED"
    result = StepResult(output={}, status="success")

    update = await adapter.evaluate_progress(sample_plan, result)

    assert update.action == "abort"
    assert "already in FAILED state" in update.reason
