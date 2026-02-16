"""
Tests for CrewAI Adapter

Tests for CrewAIAdapter implementation.
Note: These tests mock CrewAI to avoid external dependencies.
"""

import pytest
from unittest.mock import MagicMock

from framework.engine.crewai_adapter import CrewAIAdapter
from framework.actor import Actor, ActorRegistry
from framework.types import PlanStep


class SimpleActor(Actor):
    """Simple test actor."""

    def configure(self) -> None:
        self.name = "SimpleActor"
        self.description = "A simple test actor"
        self.goal = "Test things"
        self.tools = [self.greet, self.add]
        self.llm_config = None

    def greet(self, name: str) -> str:
        """Say hello"""
        return f"Hello, {name}!"

    def add(self, a: int, b: int) -> int:
        """Add numbers"""
        return a + b


class TestCrewAIAdapterInit:
    """Tests for CrewAIAdapter initialization."""

    def test_init_default(self):
        """CrewAIAdapter should initialize with defaults."""
        ActorRegistry.clear()
        adapter = CrewAIAdapter()

        assert adapter is not None
        assert hasattr(adapter, "_event_bus")

    def test_init_with_llm_client(self):
        """CrewAIAdapter should accept llm_client parameter."""
        ActorRegistry.clear()
        mock_client = MagicMock()
        adapter = CrewAIAdapter(llm_client=mock_client)

        assert adapter is not None
        assert adapter.llm_client == mock_client


class TestCrewAIAdapterWithActor:
    """Tests for CrewAIAdapter with registered actors."""

    @pytest.mark.asyncio
    async def test_generate_plan_fallback(self):
        """CrewAIAdapter should generate fallback plan when no LLM client."""
        ActorRegistry.clear()
        actor = SimpleActor()
        actor.configure()  # Ensure actor is configured
        ActorRegistry.register("SimpleActor", SimpleActor)

        # No LLM client - should use fallback
        adapter = CrewAIAdapter(llm_client=None)
        plan = await adapter.generate_plan("Say hello", [actor])

        assert plan is not None
        assert len(plan.steps) > 0
        assert plan.steps[0].actor_name == "SimpleActor"

    @pytest.mark.asyncio
    async def test_execute_step_with_context(self, monkeypatch):
        """CrewAIAdapter should execute steps with context via CrewAI."""
        ActorRegistry.clear()
        ActorRegistry.register("SimpleActor", SimpleActor)

        # Mock CrewAI to avoid external dependencies
        mock_result = "Hello, World!"
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class = MagicMock(return_value=mock_crew_instance)

        import sys

        mock_crewai = MagicMock()
        mock_crewai.Crew = mock_crew_class
        mock_crewai.Agent = MagicMock()
        mock_crewai.Task = MagicMock()
        mock_crewai.Process = MagicMock()
        sys.modules["crewai"] = mock_crewai

        adapter = CrewAIAdapter()

        step = PlanStep(
            actor_name="SimpleActor", tool_name="greet", parameters={"name": "World"}
        )

        # execute_step requires context parameter
        result = await adapter.execute_step(step, context={})

        assert result is not None
        assert hasattr(result, "output")


class TestCrewAIAdapterLogging:
    """Tests for CrewAIAdapter logging functionality."""

    def test_instance_logger_exists(self):
        """CrewAIAdapter instances should have their own logger."""
        adapter = CrewAIAdapter()

        assert hasattr(adapter, "logger")
        assert adapter.logger is not None
        assert adapter.logger.name == "crewai_adapter"

    @pytest.mark.asyncio
    async def test_execute_step_sets_logging_context(self):
        """execute_step should call set_logging_context with actor_name and step_id."""
        from unittest.mock import patch

        ActorRegistry.clear()
        ActorRegistry.register("SimpleActor", SimpleActor)

        adapter = CrewAIAdapter()

        step = PlanStep(
            actor_name="SimpleActor",
            tool_name="greet",
            parameters={"name": "World"},
        )

        # Mock set_logging_context to verify it's called
        with patch(
            "framework.engine.crewai_adapter.set_logging_context"
        ) as mock_set_context:
            # CrewAI missing → error path, but set_logging_context should still be called
            result = await adapter.execute_step(step, context={})

            # Verify set_logging_context was called with correct parameters
            mock_set_context.assert_called_once_with(
                actor_name="SimpleActor",
                step_id=step.id,
            )

        # Verify result
        assert result is not None
        assert result.status == "error"  # CrewAI not available
