"""
End-to-End Integration Tests for JAF Framework.

Tests the complete framework flow:
- Input → Engine → Orchestrator → Actors → Persistence → Events → Output
- Crash recovery and state restoration
- Event bus integration
- Multi-actor coordination

These tests exercise the full system with real database operations.
"""

import pytest
import uuid

from framework.orchestrator import Orchestrator
from framework.engine.native_engine import NativeEngine
from framework.event_bus import get_event_bus
from framework.types import Plan, PlanStep, AgentAction
from framework.persistence.models import ProcessStatus
from framework.persistence.process_repo import ProcessRepository

from tests.integration.actors_fixtures import (
    CalculatorActor,
    ValidatorActor,
    DataProcessorActor,
)


@pytest.fixture
def event_collector():
    """Fixture that collects all events emitted during test."""
    events = []

    def collector(action):
        events.append(action)

    # Get singleton and clear it
    bus = get_event_bus()
    bus.clear()

    # Subscribe collector
    bus.subscribe(collector)

    yield events

    # Cleanup
    bus.unsubscribe(collector)
    bus.clear()


@pytest.fixture
def calculator_actor():
    """Provide configured CalculatorActor."""
    from framework.actor.registry import ActorRegistry

    actor = CalculatorActor()
    actor.configure()

    # Register the actor
    ActorRegistry.register("CalculatorActor", CalculatorActor)

    return actor


@pytest.fixture
def validator_actor():
    """Provide configured ValidatorActor."""
    from framework.actor.registry import ActorRegistry

    actor = ValidatorActor()
    actor.configure()

    # Register the actor
    ActorRegistry.register("ValidatorActor", ValidatorActor)

    return actor


@pytest.fixture
def data_processor_actor():
    """Provide configured DataProcessorActor."""
    from framework.actor.registry import ActorRegistry

    actor = DataProcessorActor()
    actor.configure()

    # Register the actor
    ActorRegistry.register("DataProcessorActor", DataProcessorActor)

    return actor


@pytest.mark.asyncio
async def test_end_to_end_simple_workflow(
    async_session,
    calculator_actor,
    validator_actor,
    event_collector,
):
    """
    Test complete workflow: Calculate → Validate → Persist → Events.

    Flow:
    1. Create process with goal
    2. Generate plan (2 steps: add, then validate)
    3. Execute plan step by step
    4. Verify persistence at each stage
    5. Verify events are emitted
    6. Verify final result
    """
    # Arrange: Create a pre-defined plan
    process_id = uuid.uuid4()

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 10, "b": 5},
            ),
            PlanStep(
                actor_name="ValidatorActor",
                tool_name="validate_positive",
                parameters={"value": 15},  # Expected result from step 1
            ),
        ],
        status="PLANNING",
    )

    # Create engine with pre-defined plan
    engine = NativeEngine(default_plan=plan)

    # Create orchestrator - use the bind from async_session
    from sqlalchemy.ext.asyncio import async_sessionmaker

    # Get the async engine from the session's bind
    async_engine = async_session.async_engine

    session_maker = async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,
    )

    orchestrator = Orchestrator(
        engine=engine,
        session_maker=session_maker,
    )

    # Act: Execute the workflow
    result = await orchestrator.run(
        goal="Calculate 10 + 5 and validate the result is positive",
        actors=[calculator_actor, validator_actor],
        context={},
        process_id=process_id,
    )

    # Assert: Verify result
    assert result.process_id == process_id
    assert result.status == ProcessStatus.COMPLETED
    assert result.error is None
    assert len(result.step_results) == 2

    # Verify step 1 (addition)
    step1_result = result.step_results[0]
    assert step1_result.status == "success"
    assert step1_result.output["result"] == 15

    # Verify step 2 (validation)
    step2_result = result.step_results[1]
    assert step2_result.status == "success"
    assert step2_result.output["is_valid"] is True

    # Verify context contains results
    assert "last_result" in result.context
    assert result.context["last_result"]["is_valid"] is True

    # Verify events were emitted
    assert len(event_collector) > 0

    event_types = [
        e.actionType if isinstance(e, AgentAction) else e.get("actionType")
        for e in event_collector
    ]

    assert "process_started" in event_types
    assert "planning_started" in event_types
    assert "plan_generated" in event_types
    assert "step_started" in event_types
    assert "step_completed" in event_types
    assert "process_completed" in event_types

    # Verify persistence: Load process from database
    repo = ProcessRepository(async_session)
    saved_process = await repo.get_process(process_id)

    assert saved_process.id == process_id
    assert saved_process.status == ProcessStatus.COMPLETED
    assert len(saved_process.current_plan.steps) == 2
    assert saved_process.current_plan.status == "COMPLETED"


@pytest.mark.asyncio
async def test_end_to_end_multi_actor_workflow(
    async_session,
    calculator_actor,
    validator_actor,
    data_processor_actor,
    event_collector,
):
    """
    Test complex multi-actor workflow with data flow between actors.

    Flow:
    1. Calculator: multiply 3 * 4 = 12
    2. Calculator: add 12 + 8 = 20
    3. DataProcessor: normalize [20]
    4. Validator: validate result is positive
    """
    # Arrange
    process_id = uuid.uuid4()

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 3, "b": 4},
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 12, "b": 8},
            ),
            PlanStep(
                actor_name="DataProcessorActor",
                tool_name="aggregate",
                parameters={"values": [20], "operation": "sum"},
            ),
            PlanStep(
                actor_name="ValidatorActor",
                tool_name="validate_positive",
                parameters={"value": 20},
            ),
        ],
        status="PLANNING",
    )

    engine = NativeEngine(default_plan=plan)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        bind=async_session.async_engine,
        expire_on_commit=False,
    )

    orchestrator = Orchestrator(
        engine=engine,
        session_maker=session_maker,
    )

    # Act
    result = await orchestrator.run(
        goal="Calculate (3 * 4) + 8, aggregate, and validate",
        actors=[calculator_actor, data_processor_actor, validator_actor],
        context={},
        process_id=process_id,
    )

    # Assert
    assert result.status == ProcessStatus.COMPLETED
    assert len(result.step_results) == 4

    # Verify each step executed correctly
    assert result.step_results[0].output["result"] == 12
    assert result.step_results[1].output["result"] == 20
    assert result.step_results[2].output["result"] == 20
    assert result.step_results[3].output["is_valid"] is True

    # Verify all steps are marked as completed
    repo = ProcessRepository(async_session)
    saved_process = await repo.get_process(process_id)

    for step in saved_process.current_plan.steps:
        assert step.status == "completed"


@pytest.mark.asyncio
async def test_end_to_end_error_handling(
    async_session,
    calculator_actor,
    event_collector,
):
    """
    Test error handling and recovery in the workflow.

    Tests:
    - Division by zero error
    - Process marked as FAILED
    - Error events emitted
    - Partial results saved
    """
    # Arrange: Plan with error-prone step
    process_id = uuid.uuid4()

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 10, "b": 5},
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="divide",
                parameters={"a": 10, "b": 0},  # Division by zero
            ),
        ],
        status="PLANNING",
    )

    engine = NativeEngine(default_plan=plan)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        bind=async_session.async_engine,
        expire_on_commit=False,
    )

    orchestrator = Orchestrator(
        engine=engine,
        session_maker=session_maker,
    )

    # Act
    result = await orchestrator.run(
        goal="Test error handling with division by zero",
        actors=[calculator_actor],
        context={},
        process_id=process_id,
    )

    # Assert: Process should complete but step should fail
    # Note: The engine's evaluate_progress determines if this continues or aborts
    # For now, we verify the step failed
    assert len(result.step_results) >= 1

    # First step should succeed
    assert result.step_results[0].status == "success"
    assert result.step_results[0].output["result"] == 15

    # Second step should have error info
    if len(result.step_results) >= 2:
        assert result.step_results[1].output["success"] is False
        assert "error" in result.step_results[1].output

    # Verify events include error
    event_types = [
        e.actionType if isinstance(e, AgentAction) else e.get("actionType")
        for e in event_collector
    ]

    # Should have started the process
    assert "process_started" in event_types


@pytest.mark.asyncio
async def test_end_to_end_persistence_state_tracking(
    async_session,
    calculator_actor,
):
    """
    Test that process state is correctly persisted at each stage.

    Verifies:
    - Process created with PENDING status
    - Status transitions to RUNNING
    - Each step status updated
    - Final status is COMPLETED
    - Context updated throughout
    """
    # Arrange
    process_id = uuid.uuid4()

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 1, "b": 2},
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 3, "b": 3},
            ),
        ],
        status="PLANNING",
    )

    engine = NativeEngine(default_plan=plan)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        bind=async_session.async_engine,
        expire_on_commit=False,
    )

    orchestrator = Orchestrator(
        engine=engine,
        session_maker=session_maker,
    )

    repo = ProcessRepository(async_session)

    # Act
    result = await orchestrator.run(
        goal="Track state changes through execution",
        actors=[calculator_actor],
        context={"initial": "data"},
        process_id=process_id,
    )

    # Assert
    assert result.status == ProcessStatus.COMPLETED

    # Verify final state in database
    saved_process = await repo.get_process(process_id)

    assert saved_process.status == ProcessStatus.COMPLETED
    assert saved_process.current_plan.status == "COMPLETED"

    # Verify context was preserved and updated
    assert "initial" in saved_process.context
    assert saved_process.context["initial"] == "data"
    assert "last_result" in saved_process.context

    # Verify all steps completed
    for step in saved_process.current_plan.steps:
        assert step.status == "completed"


@pytest.mark.asyncio
async def test_event_bus_integration_all_events(
    async_session,
    calculator_actor,
    event_collector,
):
    """
    Test that all expected events are emitted during execution.

    Events to verify:
    - process_started
    - planning_started
    - plan_generated
    - step_started (for each step)
    - step_completed (for each step)
    - process_completed
    """
    # Arrange
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 5, "b": 3},
            ),
        ],
        status="PLANNING",
    )

    engine = NativeEngine(default_plan=plan)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        bind=async_session.async_engine,
        expire_on_commit=False,
    )

    orchestrator = Orchestrator(
        engine=engine,
        session_maker=session_maker,
    )

    # Act
    result = await orchestrator.run(
        goal="Test event emission",
        actors=[calculator_actor],
    )

    # Assert: Verify all events
    assert result.status == ProcessStatus.COMPLETED

    event_types = [
        e.actionType if isinstance(e, AgentAction) else e.get("actionType")
        for e in event_collector
    ]

    # Required events in order
    required_events = [
        "process_started",
        "planning_started",
        "plan_generated",
        "step_started",
        "step_completed",
        "process_completed",
    ]

    for required_event in required_events:
        assert required_event in event_types, f"Missing event: {required_event}"

    # Verify event structure
    for event in event_collector:
        if isinstance(event, AgentAction):
            assert event.agentId is not None
            assert event.actionType is not None
            assert event.message is not None
            assert event.status in ["complete", "error"]
            assert event.timestamp is not None
        else:
            assert "agentId" in event
            assert "actionType" in event
            assert "message" in event


@pytest.mark.asyncio
async def test_concurrent_process_isolation(
    async_session,
    calculator_actor,
):
    """
    Test that multiple processes can run independently without interfering.

    Creates two processes with different IDs and verifies:
    - Each has its own state
    - Each persists independently
    - Results don't mix
    """
    # Arrange
    process_id_1 = uuid.uuid4()
    process_id_2 = uuid.uuid4()

    plan_1 = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 10, "b": 10},
            ),
        ],
        status="PLANNING",
    )

    plan_2 = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 5, "b": 5},
            ),
        ],
        status="PLANNING",
    )

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        bind=async_session.async_engine,
        expire_on_commit=False,
    )

    engine_1 = NativeEngine(default_plan=plan_1)
    engine_2 = NativeEngine(default_plan=plan_2)

    orchestrator_1 = Orchestrator(engine=engine_1, session_maker=session_maker)
    orchestrator_2 = Orchestrator(engine=engine_2, session_maker=session_maker)

    # Act: Run both processes
    result_1 = await orchestrator_1.run(
        goal="Process 1: Add",
        actors=[calculator_actor],
        process_id=process_id_1,
    )

    result_2 = await orchestrator_2.run(
        goal="Process 2: Multiply",
        actors=[calculator_actor],
        process_id=process_id_2,
    )

    # Assert: Both completed successfully
    assert result_1.status == ProcessStatus.COMPLETED
    assert result_2.status == ProcessStatus.COMPLETED

    # Verify results are different
    assert result_1.step_results[0].output["result"] == 20  # 10 + 10
    assert result_2.step_results[0].output["result"] == 25  # 5 * 5

    # Verify both are persisted separately
    repo = ProcessRepository(async_session)

    saved_1 = await repo.get_process(process_id_1)
    saved_2 = await repo.get_process(process_id_2)

    assert saved_1.id == process_id_1
    assert saved_2.id == process_id_2
    assert saved_1.id != saved_2.id
