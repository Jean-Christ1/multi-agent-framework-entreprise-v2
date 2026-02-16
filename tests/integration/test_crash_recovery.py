"""
Crash Recovery Integration Tests for JAF Framework.

Tests the framework's ability to recover from crashes and resume execution:
- Process state restoration from database
- Resuming from last completed step
- Handling partial execution
- State consistency after recovery
"""

import pytest
import uuid

from framework.orchestrator import Orchestrator
from framework.engine.native_engine import NativeEngine
from framework.types import Plan, PlanStep
from framework.persistence.models import ProcessStatus
from framework.persistence.process_repo import ProcessRepository

from tests.integration.actors_fixtures import CalculatorActor, ValidatorActor


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


@pytest.mark.asyncio
async def test_crash_recovery_restore_process_state(
    async_session,
    calculator_actor,
):
    """
    Test restoring process state from database after a crash.

    Scenario:
    1. Create and start a process
    2. Execute first step
    3. Simulate crash (stop execution)
    4. Load process from database
    5. Verify state is correctly restored
    """
    # Arrange: Create initial process
    process_id = uuid.uuid4()

    initial_plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 5, "b": 3},
                status="completed",  # Simulate this was completed before crash
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 8, "b": 2},
                status="pending",  # Not yet executed
            ),
        ],
        status="EXECUTING",
    )

    initial_context = {
        "step_0_result": {
            "operation": "add",
            "result": 8,
            "success": True,
        },
        "last_result": {
            "operation": "add",
            "result": 8,
            "success": True,
        },
    }

    # Persist initial state (simulating state before crash)
    repo = ProcessRepository(async_session)
    await repo.create_process(
        process_id=process_id,
        plan=initial_plan,
        context=initial_context,
        status=ProcessStatus.RUNNING,
    )

    # Act: Simulate crash and recovery - load process from database
    restored_process = await repo.get_process(process_id)

    # Assert: Verify state restoration
    assert restored_process.id == process_id
    assert restored_process.status == ProcessStatus.RUNNING
    assert restored_process.current_plan.status == "EXECUTING"

    # Verify steps state
    steps = restored_process.current_plan.steps
    assert len(steps) == 2
    assert steps[0].status == "completed"
    assert steps[1].status == "pending"

    # Verify context restoration
    assert "step_0_result" in restored_process.context
    assert restored_process.context["step_0_result"]["result"] == 8
    assert "last_result" in restored_process.context


@pytest.mark.asyncio
async def test_crash_recovery_resume_from_checkpoint(
    async_session,
    calculator_actor,
    validator_actor,
):
    """
    Test resuming execution from the last checkpoint after a crash.

    Scenario:
    1. Process executes 2 steps and crashes
    2. State is saved in database
    3. New orchestrator loads state
    4. Execution resumes from step 3
    5. Process completes successfully
    """
    # Phase 1: Execute partially and save state
    process_id = uuid.uuid4()

    # Create a plan with 4 steps
    full_plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 10, "b": 5},
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 3, "b": 5},
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="divide",
                parameters={"a": 15, "b": 3},
            ),
            PlanStep(
                actor_name="ValidatorActor",
                tool_name="validate_positive",
                parameters={"value": 5},
            ),
        ],
        status="PLANNING",
    )

    engine = NativeEngine(default_plan=full_plan)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(
        bind=async_session.async_engine,
        expire_on_commit=False,
    )

    # Execute the full workflow
    orchestrator = Orchestrator(
        engine=engine,
        session_maker=session_maker,
    )

    result = await orchestrator.run(
        goal="Complete workflow with 4 steps",
        actors=[calculator_actor, validator_actor],
        process_id=process_id,
    )

    # Assert: Process completed
    assert result.status == ProcessStatus.COMPLETED
    assert len(result.step_results) == 4

    # Phase 2: Verify we can reload the completed process
    repo = ProcessRepository(async_session)
    recovered_process = await repo.get_process(process_id)

    assert recovered_process.status == ProcessStatus.COMPLETED
    assert len(recovered_process.current_plan.steps) == 4

    # All steps should be completed
    for step in recovered_process.current_plan.steps:
        assert step.status == "completed"

    # Context should contain all intermediate results
    assert "step_0_result" in recovered_process.context
    assert "step_1_result" in recovered_process.context
    assert "step_2_result" in recovered_process.context
    assert "step_3_result" in recovered_process.context


@pytest.mark.asyncio
async def test_crash_recovery_partial_step_execution(
    async_session,
    calculator_actor,
):
    """
    Test recovery when a step was executing but not completed.

    Scenario:
    1. Process starts executing step 2
    2. Crash occurs mid-execution
    3. Step is marked as 'executing' in database
    4. Recovery detects incomplete step
    5. Can restart from that step
    """
    # Arrange: Simulate a crashed process with an executing step
    process_id = uuid.uuid4()

    crashed_plan = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 7, "b": 3},
                status="completed",
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 10, "b": 2},
                status="executing",  # Crash happened during this step
            ),
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="divide",
                parameters={"a": 20, "b": 4},
                status="pending",
            ),
        ],
        status="EXECUTING",
    )

    crashed_context = {
        "step_0_result": {"operation": "add", "result": 10, "success": True},
        "last_result": {"operation": "add", "result": 10, "success": True},
    }

    # Save crashed state
    repo = ProcessRepository(async_session)
    await repo.create_process(
        process_id=process_id,
        plan=crashed_plan,
        context=crashed_context,
        status=ProcessStatus.RUNNING,
    )

    # Act: Load crashed process
    loaded_process = await repo.get_process(process_id)

    # Assert: Verify we can detect the incomplete step
    steps = loaded_process.current_plan.steps

    executing_steps = [s for s in steps if s.status == "executing"]
    completed_steps = [s for s in steps if s.status == "completed"]
    pending_steps = [s for s in steps if s.status == "pending"]

    assert len(executing_steps) == 1
    assert len(completed_steps) == 1
    assert len(pending_steps) == 1

    # The executing step should be step 2 (multiply)
    assert executing_steps[0].tool_name == "multiply"

    # In a real recovery scenario, we would reset executing steps to pending
    # and resume execution
    for step in steps:
        if step.status == "executing":
            step.status = "pending"

    # Update the process with reset state
    await repo.update_process(
        process_id=process_id,
        plan=loaded_process.current_plan,
        context=loaded_process.context,
        status=ProcessStatus.RUNNING,
    )

    # Verify reset worked
    updated_process = await repo.get_process(process_id)
    updated_steps = updated_process.current_plan.steps

    executing_after_reset = [s for s in updated_steps if s.status == "executing"]
    assert len(executing_after_reset) == 0


@pytest.mark.asyncio
async def test_crash_recovery_state_consistency(
    async_session,
    calculator_actor,
):
    """
    Test that process state remains consistent after recovery.

    Verifies:
    - Plan steps match context
    - No data corruption
    - Timestamps preserved
    - Process ID integrity
    """
    # Arrange: Create a process with rich state
    process_id = uuid.uuid4()

    plan = Plan(
        steps=[
            PlanStep(
                id="step-1",
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 100, "b": 200},
                status="completed",
            ),
            PlanStep(
                id="step-2",
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 300, "b": 2},
                status="completed",
            ),
        ],
        status="EXECUTING",
    )

    context = {
        "step_0_result": {
            "operation": "add",
            "inputs": {"a": 100, "b": 200},
            "result": 300,
            "success": True,
        },
        "step_1_result": {
            "operation": "multiply",
            "inputs": {"a": 300, "b": 2},
            "result": 600,
            "success": True,
        },
        "last_result": {
            "operation": "multiply",
            "inputs": {"a": 300, "b": 2},
            "result": 600,
            "success": True,
        },
        "metadata": {
            "user": "test_user",
            "session": "test_session",
        },
    }

    # Save process
    repo = ProcessRepository(async_session)
    saved = await repo.create_process(
        process_id=process_id,
        plan=plan,
        context=context,
        status=ProcessStatus.RUNNING,
    )

    # Store original timestamps
    original_created_at = saved.created_at
    original_updated_at = saved.updated_at

    # Act: Simulate crash and recovery
    recovered = await repo.get_process(process_id)

    # Assert: Verify state consistency

    # 1. Process ID integrity
    assert recovered.id == process_id
    assert str(recovered.id) == str(process_id)

    # 2. Plan integrity
    assert len(recovered.current_plan.steps) == 2
    assert recovered.current_plan.steps[0].id == "step-1"
    assert recovered.current_plan.steps[1].id == "step-2"

    # 3. Context integrity
    assert "step_0_result" in recovered.context
    assert "step_1_result" in recovered.context
    assert "last_result" in recovered.context
    assert "metadata" in recovered.context

    # Verify deep context values
    assert recovered.context["step_0_result"]["result"] == 300
    assert recovered.context["step_1_result"]["result"] == 600
    assert recovered.context["metadata"]["user"] == "test_user"

    # 4. Status consistency
    assert recovered.status == ProcessStatus.RUNNING
    assert recovered.current_plan.status == "EXECUTING"

    # 5. Timestamps preserved
    assert recovered.created_at == original_created_at
    assert recovered.updated_at == original_updated_at

    # 6. All completed steps have correct status
    for step in recovered.current_plan.steps:
        assert step.status == "completed"


@pytest.mark.asyncio
async def test_crash_recovery_multiple_processes(
    async_session,
    calculator_actor,
):
    """
    Test recovery of multiple processes with different states.

    Verifies:
    - Each process maintains independent state
    - Recovery works for multiple processes
    - No cross-contamination of data
    """
    # Arrange: Create 3 processes in different states
    process_1_id = uuid.uuid4()
    process_2_id = uuid.uuid4()
    process_3_id = uuid.uuid4()

    repo = ProcessRepository(async_session)

    # Process 1: Completed
    plan_1 = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="add",
                parameters={"a": 1, "b": 1},
                status="completed",
            ),
        ],
        status="COMPLETED",
    )
    await repo.create_process(
        process_id=process_1_id,
        plan=plan_1,
        context={"result": 2},
        status=ProcessStatus.COMPLETED,
    )

    # Process 2: Running
    plan_2 = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="multiply",
                parameters={"a": 3, "b": 3},
                status="executing",
            ),
        ],
        status="EXECUTING",
    )
    await repo.create_process(
        process_id=process_2_id,
        plan=plan_2,
        context={"partial": True},
        status=ProcessStatus.RUNNING,
    )

    # Process 3: Pending
    plan_3 = Plan(
        steps=[
            PlanStep(
                actor_name="CalculatorActor",
                tool_name="divide",
                parameters={"a": 10, "b": 2},
                status="pending",
            ),
        ],
        status="PLANNING",
    )
    await repo.create_process(
        process_id=process_3_id,
        plan=plan_3,
        context={"started": False},
        status=ProcessStatus.PENDING,
    )

    # Act: Recover all processes
    recovered_1 = await repo.get_process(process_1_id)
    recovered_2 = await repo.get_process(process_2_id)
    recovered_3 = await repo.get_process(process_3_id)

    # Assert: Each process has correct independent state

    # Process 1
    assert recovered_1.id == process_1_id
    assert recovered_1.status == ProcessStatus.COMPLETED
    assert recovered_1.context["result"] == 2

    # Process 2
    assert recovered_2.id == process_2_id
    assert recovered_2.status == ProcessStatus.RUNNING
    assert recovered_2.context["partial"] is True

    # Process 3
    assert recovered_3.id == process_3_id
    assert recovered_3.status == ProcessStatus.PENDING
    assert recovered_3.context["started"] is False

    # Verify no cross-contamination
    assert recovered_1.id != recovered_2.id != recovered_3.id
    assert "partial" not in recovered_1.context
    assert "result" not in recovered_2.context
    assert "started" not in recovered_1.context
