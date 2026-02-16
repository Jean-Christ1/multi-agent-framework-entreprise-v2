"""
Unit tests for JAF framework types.

Tickets: JAF-4, JAF-16, JAF-29
"""

import pytest
from datetime import datetime

from framework.types import (
    LLMConfig,
    Plan,
    PlanStep,
    PlanUpdate,
    StepResult,
    AgentAction,
)


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_create_valid_config(self):
        """Should create a valid LLMConfig."""
        config = LLMConfig(model="gpt-4o", temperature=0.5, max_tokens=1000)

        assert config.model == "gpt-4o"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000

    def test_default_temperature(self):
        """Temperature should default to 0.0."""
        config = LLMConfig(model="gpt-4o")
        assert config.temperature == 0.0

    def test_optional_max_tokens(self):
        """max_tokens should be optional."""
        config = LLMConfig(model="gpt-4o")
        assert config.max_tokens is None

    def test_temperature_bounds(self):
        """Temperature must be between 0.0 and 2.0."""
        with pytest.raises(ValueError):
            LLMConfig(model="gpt-4o", temperature=-0.1)

        with pytest.raises(ValueError):
            LLMConfig(model="gpt-4o", temperature=2.1)

    def test_max_tokens_must_be_positive(self):
        """max_tokens must be > 0 if provided."""
        with pytest.raises(ValueError):
            LLMConfig(model="gpt-4o", max_tokens=0)

    def test_config_is_frozen(self):
        """LLMConfig instances should be immutable."""
        config = LLMConfig(model="gpt-4o")
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            config.model = "gpt-4o-mini"

    def test_any_model_name_accepted(self):
        """Any model name should be accepted (no hardcoded whitelist)."""
        # This should NOT raise an error
        config = LLMConfig(model="claude-3-opus")
        assert config.model == "claude-3-opus"

        config2 = LLMConfig(model="custom-model-v2")
        assert config2.model == "custom-model-v2"


class TestPlanStep:
    """Tests for PlanStep."""

    def test_create_plan_step(self):
        """Should create a valid PlanStep."""
        step = PlanStep(
            actor_name="TestActor",
            tool_name="test_tool",
            parameters={"key": "value"},
        )

        assert step.actor_name == "TestActor"
        assert step.tool_name == "test_tool"
        assert step.parameters == {"key": "value"}
        assert step.status == "pending"

    def test_step_has_uuid_id(self):
        """PlanStep should have an auto-generated UUID id."""
        step = PlanStep(
            actor_name="TestActor",
            tool_name="test_tool",
            parameters={},
        )

        assert step.id is not None
        assert len(step.id) == 36  # UUID format

    def test_step_status_values(self):
        """PlanStep status should accept valid values."""
        for status in ["pending", "executing", "completed", "failed"]:
            step = PlanStep(
                actor_name="TestActor",
                tool_name="test_tool",
                parameters={},
                status=status,
            )
            assert step.status == status


class TestPlan:
    """Tests for Plan."""

    def test_create_plan(self):
        """Should create a valid Plan."""
        step = PlanStep(
            actor_name="TestActor",
            tool_name="test_tool",
            parameters={},
        )
        plan = Plan(steps=[step])

        assert len(plan.steps) == 1
        assert plan.status == "PLANNING"
        assert plan.created_at is not None

    def test_next_step_returns_first_pending(self):
        """next_step() should return the first pending step."""
        step1 = PlanStep(
            actor_name="Actor1",
            tool_name="tool1",
            parameters={},
            status="completed",
        )
        step2 = PlanStep(
            actor_name="Actor2",
            tool_name="tool2",
            parameters={},
            status="pending",
        )
        plan = Plan(steps=[step1, step2])

        next_step = plan.next_step()
        assert next_step == step2

    def test_next_step_returns_none_when_all_complete(self):
        """next_step() should return None when all steps are complete."""
        step = PlanStep(
            actor_name="Actor1",
            tool_name="tool1",
            parameters={},
            status="completed",
        )
        plan = Plan(steps=[step])

        assert plan.next_step() is None

    def test_to_mermaid_empty_plan(self):
        """to_mermaid() should return valid Mermaid for empty plan."""
        plan = Plan(steps=[], status="PLANNING")
        m = plan.to_mermaid()
        assert m.startswith("flowchart TD")
        assert "empty plan" in m

    def test_to_mermaid_shows_actor_tool_names(self):
        """to_mermaid() should show steps as actor.tool names."""
        step = PlanStep(
            actor_name="ProvisioningActor",
            tool_name="create_order",
            parameters={},
            status="pending",
        )
        plan = Plan(steps=[step])
        m = plan.to_mermaid()
        assert "ProvisioningActor.create_order" in m
        assert "s0" in m

    def test_to_mermaid_parallel_groups_as_parallel_nodes(self):
        """to_mermaid() should connect parallel group steps as parallel branches."""
        plan = Plan(
            steps=[
                PlanStep(
                    actor_name="A",
                    tool_name="t1",
                    parameters={},
                    status="completed",
                    parallel_group=None,
                ),
                PlanStep(
                    actor_name="B",
                    tool_name="t2",
                    parameters={},
                    status="pending",
                    parallel_group="p",
                ),
                PlanStep(
                    actor_name="C",
                    tool_name="t3",
                    parameters={},
                    status="pending",
                    parallel_group="p",
                ),
                PlanStep(
                    actor_name="D",
                    tool_name="t4",
                    parameters={},
                    status="pending",
                    parallel_group=None,
                ),
            ],
            status="EXECUTING",
        )
        m = plan.to_mermaid()
        # s0 -> s1 and s0 -> s2 (parallel from first step)
        assert "s0 --> s1" in m
        assert "s0 --> s2" in m
        # s1 and s2 -> s3 (merge after parallel)
        assert "s1 --> s3" in m
        assert "s2 --> s3" in m

    def test_to_mermaid_step_status_colors(self):
        """to_mermaid() should include style lines for step status (completed=green, failed=red, pending=gray)."""
        plan = Plan(
            steps=[
                PlanStep(
                    actor_name="A", tool_name="t1", parameters={}, status="completed"
                ),
                PlanStep(
                    actor_name="B", tool_name="t2", parameters={}, status="failed"
                ),
                PlanStep(
                    actor_name="C", tool_name="t3", parameters={}, status="pending"
                ),
            ],
            status="EXECUTING",
        )
        m = plan.to_mermaid()
        assert "style s0 fill:#c8e6c9" in m  # completed = green
        assert "style s1 fill:#ffcdd2" in m  # failed = red
        assert "style s2 fill:#e0e0e0" in m  # pending = gray


class TestStepResult:
    """Tests for StepResult."""

    def test_create_success_result(self):
        """Should create a success StepResult."""
        result = StepResult(
            output={"data": "value"},
            status="success",
        )

        assert result.output == {"data": "value"}
        assert result.status == "success"
        assert result.error is None

    def test_create_error_result(self):
        """Should create an error StepResult."""
        result = StepResult(
            output={},
            status="error",
            error="Something went wrong",
        )

        assert result.status == "error"
        assert result.error == "Something went wrong"


class TestPlanUpdate:
    """Tests for PlanUpdate."""

    def test_create_continue_update(self):
        """Should create a continue PlanUpdate."""
        update = PlanUpdate(action="continue", reason="Step succeeded")

        assert update.action == "continue"
        assert update.reason == "Step succeeded"
        assert update.modified_plan is None

    def test_create_modify_update_with_plan(self):
        """Should create a modify PlanUpdate with new plan."""
        step = PlanStep(
            actor_name="NewActor",
            tool_name="new_tool",
            parameters={},
        )
        new_plan = Plan(steps=[step])

        update = PlanUpdate(
            action="modify",
            modified_plan=new_plan,
            reason="Need to add a step",
        )

        assert update.action == "modify"
        assert update.modified_plan is not None


class TestAgentAction:
    """Tests for AgentAction."""

    def test_create_agent_action(self):
        """Should create a valid AgentAction."""
        action = AgentAction(
            agentId="TestAgent",
            actionType="execute_tool",
            message="Executed successfully",
            status="complete",
        )

        assert action.agentId == "TestAgent"
        assert action.actionType == "execute_tool"
        assert action.message == "Executed successfully"
        assert action.status == "complete"

    def test_timestamp_auto_generated(self):
        """AgentAction should have auto-generated ISO timestamp."""
        action = AgentAction(
            agentId="TestAgent",
            actionType="test",
            message="Test",
            status="complete",
        )

        assert action.timestamp.endswith("Z")
        # Should be parseable as ISO format
        timestamp_str = action.timestamp.rstrip("Z")
        datetime.fromisoformat(timestamp_str)

    def test_status_values(self):
        """AgentAction status should be 'complete' or 'error'."""
        for status in ["complete", "error"]:
            action = AgentAction(
                agentId="TestAgent",
                actionType="test",
                message="Test",
                status=status,
            )
            assert action.status == status
