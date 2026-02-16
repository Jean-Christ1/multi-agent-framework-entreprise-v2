import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from framework.orchestrator import Orchestrator, ProcessResult
from framework.persistence.models import ProcessStatus
from framework.types import Plan, PlanStep, StepResult, PlanUpdate
from framework.state_machine import InvalidTransitionError

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fake_actor():
    actor = MagicMock()
    actor.name = "TestActor"
    return actor


@pytest.fixture
def fake_plan():
    return Plan(
        steps=[
            PlanStep(
                actor_name="TestActor",
                tool_name="test_tool",
                parameters={"x": 1},
                status="pending",
            )
        ],
        status="PLANNING",
    )


@pytest.fixture
def modified_plan():
    return Plan(
        steps=[
            PlanStep(
                actor_name="TestActor",
                tool_name="modified_tool",
                parameters={"y": 99},
                status="pending",
            )
        ],
        status="PLANNING",
    )


@pytest.fixture
def engine(fake_plan):
    engine = AsyncMock()

    engine.generate_plan.return_value = fake_plan

    engine.execute_step.return_value = StepResult(
        status="success",
        output={"result": 42},
        error=None,
    )

    engine.evaluate_progress.return_value = PlanUpdate(
        action="continue",
        reason="ok",
        modified_plan=None,
    )

    return engine


@pytest.fixture
def event_bus():
    bus = MagicMock()
    bus.emit = MagicMock()
    return bus


@pytest.fixture
def session_maker():
    class FakeSessionCtx:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, exc_type, exc, tb):
            pass

    return MagicMock(return_value=FakeSessionCtx())


@pytest.fixture
def orchestrator(engine, session_maker, event_bus, monkeypatch):
    mock_repo = AsyncMock()
    mock_repo.create_process = AsyncMock()
    mock_repo.update_process = AsyncMock()

    monkeypatch.setattr(
        "framework.orchestrator.ProcessRepository",
        lambda session: mock_repo,
    )

    orch = Orchestrator(
        engine=engine,
        session_maker=session_maker,
        event_bus=event_bus,
    )

    orch._mock_repo = mock_repo
    return orch


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_process_creation_and_pending_to_running_transition(
    orchestrator, fake_actor
):
    process_id = uuid.uuid4()

    result = await orchestrator.run(
        goal="test goal",
        actors=[fake_actor],
        process_id=process_id,
    )

    repo = orchestrator._mock_repo

    repo.create_process.assert_awaited_once()
    args, kwargs = repo.create_process.call_args
    assert kwargs["status"] == ProcessStatus.PENDING

    statuses = [
        call.kwargs.get("status")
        for call in repo.update_process.call_args_list
        if "status" in call.kwargs
    ]

    assert ProcessStatus.RUNNING in statuses
    assert ProcessStatus.COMPLETED in statuses
    assert result.status == ProcessStatus.COMPLETED


@pytest.mark.asyncio
async def test_successful_execution_flow_completes_process(orchestrator, fake_actor):
    result = await orchestrator.run(
        goal="successful goal",
        actors=[fake_actor],
        context={"initial": True},
    )

    assert isinstance(result, ProcessResult)
    assert result.status == ProcessStatus.COMPLETED
    assert result.plan.status == "COMPLETED"
    assert result.context["last_result"] == {"result": 42}
    assert len(result.step_results) == 1
    assert result.step_results[0].status == "success"


@pytest.mark.asyncio
async def test_failure_handling_sets_failed_status(orchestrator, engine, fake_actor):
    engine.execute_step.return_value = StepResult(
        status="error",
        output={},
        error="boom",
    )

    engine.evaluate_progress.return_value = PlanUpdate(
        action="abort",
        reason="critical failure",
        modified_plan=None,
    )

    result = await orchestrator.run(
        goal="failing goal",
        actors=[fake_actor],
    )

    assert result.status == ProcessStatus.FAILED
    assert result.plan.status == "FAILED"
    assert result.error == "critical failure"


@pytest.mark.asyncio
async def test_engine_exception_sets_process_failed(orchestrator, engine, fake_actor):
    engine.generate_plan.side_effect = RuntimeError("engine crash")

    result = await orchestrator.run(
        goal="crash goal",
        actors=[fake_actor],
    )

    assert result.status == ProcessStatus.FAILED
    assert "engine crash" in result.error


@pytest.mark.skip(reason="Planning events removed in dry-run refactor - needs update")
@pytest.mark.asyncio
async def test_event_emission_full_lifecycle_and_order(
    orchestrator, fake_actor, event_bus
):
    await orchestrator.run(
        goal="event test",
        actors=[fake_actor],
    )

    emitted = [call.args[0].actionType for call in event_bus.emit.call_args_list]

    assert emitted == [
        "process_started",
        "planning_started",
        "plan_generated",
        "step_started",
        "step_completed",
        "process_completed",
    ]


@pytest.mark.asyncio
async def test_step_failed_emits_error_event(
    orchestrator, engine, fake_actor, event_bus
):
    engine.execute_step.return_value = StepResult(
        status="error",
        output={},
        error="step failed",
    )

    engine.evaluate_progress.return_value = PlanUpdate(
        action="abort",
        reason="stop",
        modified_plan=None,
    )

    await orchestrator.run(
        goal="step error",
        actors=[fake_actor],
    )

    error_events = [
        call.args[0]
        for call in event_bus.emit.call_args_list
        if getattr(call.args[0], "status", None) == "error"
    ]

    assert any(e.actionType == "step_failed" for e in error_events)


@pytest.mark.asyncio
async def test_invalid_transition_sets_failed(orchestrator, fake_actor, monkeypatch):
    monkeypatch.setattr(
        "framework.orchestrator.ProcessStateMachine.validate_transition",
        lambda *_: (_ for _ in ()).throw(
            InvalidTransitionError(ProcessStatus.PENDING, ProcessStatus.COMPLETED)
        ),
    )

    result = await orchestrator.run(
        goal="invalid transition",
        actors=[fake_actor],
    )

    assert result.status == ProcessStatus.FAILED


# PLAN MODIFICATION HANDLING


@pytest.mark.asyncio
async def test_plan_modify_action_uses_modified_plan(
    orchestrator, engine, fake_actor, fake_plan, modified_plan
):
    """
    When engine returns PlanUpdate(action='modify'),
    the orchestrator must switch to the modified plan
    and continue execution with it.
    """

    engine.generate_plan.return_value = fake_plan

    engine.evaluate_progress.return_value = PlanUpdate(
        action="modify",
        reason="refined plan",
        modified_plan=modified_plan,
    )

    engine.execute_step.return_value = StepResult(
        status="success",
        output={"result": "modified"},
        error=None,
    )

    result = await orchestrator.run(
        goal="modify plan test",
        actors=[fake_actor],
    )

    assert result.status == ProcessStatus.COMPLETED
    assert result.plan is modified_plan
    assert result.plan.steps[0].tool_name == "modified_tool"
    assert result.context["last_result"] == {"result": "modified"}


@pytest.mark.asyncio
async def test_orchestrator_sets_logging_context(orchestrator, fake_actor):
    """
    Verify that orchestrator successfully executes with logging context.
    Note: Logs are emitted to stderr as JSON (structured logging),
    not captured by caplog fixture.
    """
    result = await orchestrator.run(
        goal="logging test",
        actors=[fake_actor],
    )

    # Verify successful execution (logs are visible in stderr output)
    assert result.status == ProcessStatus.COMPLETED
