# Cookbook recipe tests (executable examples).
#
# Run:
#   pytest -q tests/test_cookbook_recipes.py
#
# Notes:
# - ActorRegistry registers CLASSES, not instances.
# - NativeEngine executes tools by looking them up on a freshly created actor
#   instance via ActorRegistry.get(...) per step.
# - These tests are intentionally minimal and deterministic.

import time
from unittest.mock import patch

import pytest

from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry
from framework.engine.native_engine import NativeEngine
from framework.types import Plan, PlanStep


@pytest.fixture(autouse=True)
def _clear_registry():
    """Ensure clean registry state between tests."""
    ActorRegistry.clear()
    yield
    ActorRegistry.clear()


# ---------------------------------------------------------------------
# 1) Recipe: Error handling in actors
# ---------------------------------------------------------------------


class FailActor(Actor):
    def configure(self) -> None:
        self.name = "fail"
        self.description = ""
        self.goal = ""
        self.tools = [self.boom]
        self.llm_config = None

    def boom(self) -> dict:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_recipe_error_handling_fail_fast():
    ActorRegistry.register("fail", FailActor)

    plan = Plan(steps=[PlanStep(actor_name="fail", tool_name="boom", parameters={})])

    engine = NativeEngine(default_plan=plan)

    with pytest.raises(RuntimeError) as exc:
        await engine.execute_plan(plan, context={})

    assert "boom" in str(exc.value)


# ---------------------------------------------------------------------
# 2) Recipe: Testing actors with mocks
# ---------------------------------------------------------------------


def provider_call(user_id: str, amount: int) -> dict:
    # Real implementation would call an external provider
    return {"charge_id": "real"}


class BillingActor(Actor):
    def configure(self) -> None:
        self.name = "billing"
        self.description = ""
        self.goal = ""
        self.tools = [self.charge_card]
        self.llm_config = None

    def charge_card(self, user_id: str, amount: int) -> dict:
        # Keep the tool as a real function so NativeEngine can match by __name__
        return provider_call(user_id, amount)


@pytest.mark.asyncio
async def test_recipe_testing_with_mocks_patch_dependency():
    ActorRegistry.register("billing", BillingActor)

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="billing",
                tool_name="charge_card",
                parameters={"user_id": "u1", "amount": 10},
            )
        ]
    )

    engine = NativeEngine(default_plan=plan)

    # Patch the dependency used by the tool (NOT the tool itself)
    with patch(__name__ + ".provider_call", return_value={"charge_id": "mocked"}):
        ctx = await engine.execute_plan(plan, context={})

    assert ctx["charge_id"] == "mocked"


# ---------------------------------------------------------------------
# 3) Recipe: Parallel step execution
# ---------------------------------------------------------------------


class ParallelA(Actor):
    def configure(self) -> None:
        self.name = "a"
        self.description = ""
        self.goal = ""
        self.tools = [self.one]
        self.llm_config = None

    async def one(self) -> dict:
        return {"x": 1}


class ParallelB(Actor):
    def configure(self) -> None:
        self.name = "b"
        self.description = ""
        self.goal = ""
        self.tools = [self.two]
        self.llm_config = None

    async def two(self) -> dict:
        return {"y": 2}


@pytest.mark.asyncio
async def test_recipe_parallel_steps_merge_context():
    ActorRegistry.register("a", ParallelA)
    ActorRegistry.register("b", ParallelB)

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="a", tool_name="one", parameters={}, parallel_group="g"
            ),
            PlanStep(
                actor_name="b", tool_name="two", parameters={}, parallel_group="g"
            ),
        ]
    )

    engine = NativeEngine(default_plan=plan)
    ctx = await engine.execute_plan(plan, context={})

    assert ctx["x"] == 1
    assert ctx["y"] == 2


# ---------------------------------------------------------------------
# 4) Recipe: Passing data between steps (context)
# ---------------------------------------------------------------------


class Producer(Actor):
    def configure(self) -> None:
        self.name = "producer"
        self.description = ""
        self.goal = ""
        self.tools = [self.make]
        self.llm_config = None

    def make(self) -> dict:
        return {"uid": "u1"}


class Consumer(Actor):
    def configure(self) -> None:
        self.name = "consumer"
        self.description = ""
        self.goal = ""
        self.tools = [self.use]
        self.llm_config = None

    def use(self, uid: str) -> dict:
        return {"seen": uid}


@pytest.mark.asyncio
async def test_recipe_context_passing_placeholder_resolution():
    ActorRegistry.register("producer", Producer)
    ActorRegistry.register("consumer", Consumer)

    plan = Plan(
        steps=[
            PlanStep(actor_name="producer", tool_name="make", parameters={}),
            PlanStep(
                actor_name="consumer",
                tool_name="use",
                parameters={"uid": "{context.uid}"},
            ),
        ]
    )

    engine = NativeEngine(default_plan=plan)
    ctx = await engine.execute_plan(plan, context={})

    assert ctx["uid"] == "u1"
    assert ctx["seen"] == "u1"


# ---------------------------------------------------------------------
# 5) Recipe: Custom plan builders
# ---------------------------------------------------------------------


class PlanBuilderActor(Actor):
    def configure(self) -> None:
        self.name = "pb"
        self.description = ""
        self.goal = ""
        self.tools = [self.do]
        self.llm_config = None

    def do(self) -> dict:
        return {"done": True}


@pytest.mark.asyncio
async def test_recipe_custom_plan_builder_is_used():
    # Register actor class used by the builder plan.
    ActorRegistry.register("pb", PlanBuilderActor)

    # Custom builder ignores tools discovery and returns a fixed plan.
    def builder(goal: str, actors: list[Actor]) -> Plan:
        return Plan(steps=[PlanStep(actor_name="pb", tool_name="do", parameters={})])

    engine = NativeEngine()
    engine.set_plan_builder(builder)

    # available_actors can be any configured instances; builder may use them.
    a = PlanBuilderActor()
    a.configure()

    plan = await engine.generate_plan(goal="anything", available_actors=[a])
    assert len(plan.steps) == 1
    assert plan.steps[0].actor_name == "pb"
    assert plan.steps[0].tool_name == "do"

    ctx = await engine.execute_plan(plan, context={})
    assert ctx["done"] is True


# ---------------------------------------------------------------------
# 6) Recipe: Retries (helper-level test)
# ---------------------------------------------------------------------


def retry(fn, retries: int = 3, backoff: float = 0.01):
    last = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(backoff * (2**i))
    raise last


def test_recipe_retry_eventual_success():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return 42

    assert retry(flaky, retries=3, backoff=0.0) == 42
    assert calls["n"] == 3
