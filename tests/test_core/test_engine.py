"""
Tests for JAF Engine Abstraction

Tests for EngineAbstraction and EngineFactory.
"""

from typing import Dict, List, Optional

import pytest

from framework.actor import Actor
from framework.engine import EngineAbstraction
from framework.types import (
    Plan,
    PlanStep,
    StepResult,
)


class MockEngine(EngineAbstraction):
    """Mock engine for testing."""

    async def plan(self, goal: str, context: Optional[Dict] = None) -> Plan:
        """Generate a simple mock plan."""
        return Plan(
            goal=goal,
            steps=[
                PlanStep(
                    actor="MockActor",
                    action="mock_action",
                    parameters=context or {},
                    order=0,
                ),
            ],
            mode=self._mode,
        )

    async def execute_step(self, step: PlanStep, context: Dict) -> StepResult:
        """Execute mock step."""
        return StepResult(
            step_id=step.id,
            status=StepStatus.SUCCESS,
            output={"mock": "result"},
            duration_ms=10,
        )

    async def evaluate(self, plan: Plan, results: List[StepResult]) -> NextAction:
        """Simple evaluation."""
        if not results:
            return NextAction(
                action=ActionType.CONTINUE,
                next_step_id=plan.steps[0].id if plan.steps else None,
            )

        # All done
        return NextAction(action=ActionType.COMPLETE)


class TestEngineAbstraction:
    """Tests for EngineAbstraction base class."""

    def test_engine_init(self):
        """Engine should initialize with mode and actors."""
        engine = MockEngine(mode=ExecutionMode.AGENTIC)
        assert engine.mode == ExecutionMode.AGENTIC
        assert engine.actors == []

    def test_engine_register_actor(self):
        """Engine should allow registering actors."""

        class TestActor(Actor):
            name = "TestActor"
            description = "Test"
            goal = "Test"

        engine = MockEngine()
        actor = TestActor()
        engine.register_actor(actor)

        assert len(engine.actors) == 1
        assert engine.get_actor("TestActor") == actor

    @pytest.mark.asyncio
    async def test_engine_plan(self):
        """Engine.plan should generate a plan."""
        engine = MockEngine()
        plan = await engine.plan("Test goal", {"key": "value"})

        assert plan.goal == "Test goal"
        assert len(plan.steps) == 1
        assert plan.steps[0].actor == "MockActor"

    @pytest.mark.asyncio
    async def test_engine_execute_step(self):
        """Engine.execute_step should return result."""
        engine = MockEngine()
        step = PlanStep(actor="Test", action="test", order=0)
        result = await engine.execute_step(step, {})

        assert result.status == StepStatus.SUCCESS
        assert result.step_id == step.id

    @pytest.mark.asyncio
    async def test_engine_run(self):
        """Engine.run should complete full workflow."""
        engine = MockEngine()
        process = await engine.run("Complete a task", {"context": "value"})

        assert process.goal == "Complete a task"
        assert process.plan is not None
        assert len(process.results) > 0
        # Note: process state depends on mock implementation


class TestEngineFactory:
    """Tests for EngineFactory."""

    def test_factory_register(self):
        """EngineFactory should register engines."""
        EngineFactory._engines.clear()  # Reset for test
        EngineFactory.register("mock", MockEngine)

        assert "mock" in EngineFactory.available_engines()

    def test_factory_create(self):
        """EngineFactory should create engines."""
        EngineFactory._engines.clear()
        EngineFactory.register("mock", MockEngine)

        engine = EngineFactory.create("mock", mode=ExecutionMode.AGENTIC)

        assert isinstance(engine, MockEngine)
        assert engine.mode == ExecutionMode.AGENTIC

    def test_factory_unknown_engine(self):
        """EngineFactory should raise for unknown engines."""
        EngineFactory._engines.clear()

        with pytest.raises(ValueError, match="Unknown engine"):
            EngineFactory.create("nonexistent")

    def test_factory_available_engines(self):
        """EngineFactory should list available engines."""
        EngineFactory._engines.clear()
        EngineFactory.register("engine1", MockEngine)
        EngineFactory.register("engine2", MockEngine)

        available = EngineFactory.available_engines()
        assert set(available) == {"engine1", "engine2"}
