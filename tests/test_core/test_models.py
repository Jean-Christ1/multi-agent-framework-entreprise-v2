"""
Tests for JAF Core Models

Tests for Pydantic models: Process, Plan, PlanStep, StepResult, etc.
"""

from datetime import datetime
from uuid import UUID

import pytest

from framework.types import (
    LLMConfig,
    Plan,
    PlanStep,
    ProcessResponse,
    ProcessState,
    StepResult,
    StepStatus,
)


class TestProcessState:
    """Tests for ProcessState enum."""

    def test_all_states_defined(self):
        """All required states should be defined."""
        expected = {
            "created",
            "planning",
            "executing",
            "evaluating",
            "waiting_input",
            "completed",
            "failed",
        }
        actual = {s.value for s in ProcessState}
        assert actual == expected

    def test_state_values_are_lowercase(self):
        """State values should be lowercase strings."""
        for state in ProcessState:
            assert state.value == state.value.lower()


class TestExecutionMode:
    """Tests for ExecutionMode enum."""

    def test_all_modes_defined(self):
        """All execution modes should be defined."""
        assert ExecutionMode.AGENTIC.value == "agentic"
        assert ExecutionMode.MULTI_AGENT.value == "multi_agent"
        assert ExecutionMode.TRADITIONAL.value == "traditional"


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_default_values(self):
        """LLMConfig should have sensible defaults."""
        config = LLMConfig()
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.timeout == 60

    def test_custom_values(self):
        """LLMConfig should accept custom values."""
        config = LLMConfig(
            model="gpt-4o",
            temperature=0.7,
            max_tokens=8192,
            timeout=120,
        )
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7

    def test_immutable(self):
        """LLMConfig should be immutable."""
        config = LLMConfig()
        with pytest.raises(Exception):  # ValidationError or similar
            config.model = "changed"


class TestPlanStep:
    """Tests for PlanStep model."""

    def test_default_id_generated(self):
        """PlanStep should generate UUID by default."""
        step = PlanStep(actor="TestActor", action="test")
        assert isinstance(step.id, UUID)

    def test_required_fields(self):
        """PlanStep requires actor and action."""
        with pytest.raises(Exception):
            PlanStep()  # Missing required fields

    def test_full_step(self):
        """PlanStep should accept all fields."""
        step = PlanStep(
            actor="MyActor",
            action="do_something",
            parameters={"key": "value"},
            description="Does something",
            order=5,
        )
        assert step.actor == "MyActor"
        assert step.action == "do_something"
        assert step.parameters == {"key": "value"}
        assert step.order == 5


class TestPlan:
    """Tests for Plan model."""

    def test_default_values(self):
        """Plan should have sensible defaults."""
        plan = Plan(goal="Test goal")
        assert isinstance(plan.id, UUID)
        assert plan.goal == "Test goal"
        assert plan.steps == []
        assert plan.mode == ExecutionMode.AGENTIC
        assert isinstance(plan.created_at, datetime)

    def test_step_count_property(self):
        """Plan.step_count should return number of steps."""
        plan = Plan(
            goal="Test",
            steps=[
                PlanStep(actor="A", action="a"),
                PlanStep(actor="B", action="b"),
            ],
        )
        assert plan.step_count == 2

    def test_get_step(self):
        """Plan.get_step should find step by ID."""
        step1 = PlanStep(actor="A", action="a")
        step2 = PlanStep(actor="B", action="b")
        plan = Plan(goal="Test", steps=[step1, step2])

        found = plan.get_step(step1.id)
        assert found == step1

        not_found = plan.get_step(UUID("00000000-0000-0000-0000-000000000000"))
        assert not_found is None


class TestStepResult:
    """Tests for StepResult model."""

    def test_success_result(self):
        """StepResult should track successful execution."""
        step_id = UUID("12345678-1234-5678-1234-567812345678")
        result = StepResult(
            step_id=step_id,
            status=StepStatus.SUCCESS,
            output={"data": "result"},
            duration_ms=150,
            tokens_used=100,
        )
        assert result.is_success
        assert result.output == {"data": "result"}

    def test_failed_result(self):
        """StepResult should track failed execution."""
        step_id = UUID("12345678-1234-5678-1234-567812345678")
        result = StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error="Something went wrong",
            duration_ms=50,
        )
        assert not result.is_success
        assert result.error == "Something went wrong"


class TestProcess:
    """Tests for Process model."""

    def test_default_values(self):
        """Process should have sensible defaults."""
        process = Process(goal="Do something")
        assert isinstance(process.id, UUID)
        assert process.goal == "Do something"
        assert process.state == ProcessState.CREATED
        assert process.plan is None
        assert process.results == []
        assert process.context == {}

    def test_is_terminal(self):
        """Process.is_terminal should identify terminal states."""
        process = Process(goal="Test")

        process.state = ProcessState.CREATED
        assert not process.is_terminal

        process.state = ProcessState.COMPLETED
        assert process.is_terminal

        process.state = ProcessState.FAILED
        assert process.is_terminal

    def test_transition_to(self):
        """Process.transition_to should update state and timestamps."""
        process = Process(goal="Test")
        original_updated = process.updated_at

        process.transition_to(ProcessState.PLANNING)
        assert process.state == ProcessState.PLANNING
        assert process.updated_at > original_updated
        assert process.completed_at is None

        process.transition_to(ProcessState.COMPLETED)
        assert process.state == ProcessState.COMPLETED
        assert process.completed_at is not None

    def test_add_result(self):
        """Process.add_result should append result and update timestamp."""
        process = Process(goal="Test")
        step_id = UUID("12345678-1234-5678-1234-567812345678")
        result = StepResult(
            step_id=step_id,
            status=StepStatus.SUCCESS,
            output="done",
        )

        process.add_result(result)
        assert len(process.results) == 1
        assert process.results[0] == result

    def test_total_tokens(self):
        """Process.total_tokens should sum tokens from all results."""
        process = Process(goal="Test")
        step_id = UUID("12345678-1234-5678-1234-567812345678")

        process.add_result(
            StepResult(
                step_id=step_id,
                status=StepStatus.SUCCESS,
                tokens_used=100,
            )
        )
        process.add_result(
            StepResult(
                step_id=step_id,
                status=StepStatus.SUCCESS,
                tokens_used=150,
            )
        )

        assert process.total_tokens == 250


class TestNextAction:
    """Tests for NextAction model."""

    def test_continue_action(self):
        """NextAction should support continue action."""
        next_step_id = UUID("12345678-1234-5678-1234-567812345678")
        action = NextAction(
            action=ActionType.CONTINUE,
            next_step_id=next_step_id,
            reason="All good",
        )
        assert action.action == ActionType.CONTINUE
        assert action.next_step_id == next_step_id

    def test_abort_action(self):
        """NextAction should support abort action."""
        action = NextAction(
            action=ActionType.ABORT,
            reason="Something failed",
        )
        assert action.action == ActionType.ABORT
        assert action.next_step_id is None


class TestAPIModels:
    """Tests for API request/response models."""

    def test_create_process_request(self):
        """CreateProcessRequest should validate input."""
        request = CreateProcessRequest(
            goal="Do something",
            mode=ExecutionMode.AGENTIC,
            context={"key": "value"},
        )
        assert request.goal == "Do something"
        assert request.mode == ExecutionMode.AGENTIC

    def test_create_process_request_defaults(self):
        """CreateProcessRequest should have defaults."""
        request = CreateProcessRequest(goal="Test")
        assert request.mode == ExecutionMode.AGENTIC
        assert request.context == {}

    def test_process_response(self):
        """ProcessResponse should serialize correctly."""
        response = ProcessResponse(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            goal="Test",
            state=ProcessState.COMPLETED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert response.id is not None
        assert response.state == ProcessState.COMPLETED
