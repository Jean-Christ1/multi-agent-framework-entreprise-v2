import asyncio
import time
import pytest

from framework.types import Plan, PlanStep
from framework.engine.native_engine import NativeEngine
from framework.actor.registry import ActorRegistry


class DummyActor:
    def __init__(self, name, tools):
        self.name = name
        self.tools = tools


@pytest.mark.asyncio
async def test_parallel_group_executes_concurrently_and_merges_context(monkeypatch):
    # This test verifies that:
    # 1) Steps with the same parallel_group run concurrently (in parallel).
    # 2) The engine waits for all parallel steps to finish before continuing.
    # 3) Outputs from all parallel steps are merged into the shared context.

    async def fetch_a():
        await asyncio.sleep(0.25)
        return {"a": 1}

    async def fetch_b():
        await asyncio.sleep(0.25)
        return {"b": 2}

    async def after():
        await asyncio.sleep(0.05)
        return {"after": True}

    actor = DummyActor("worker", [fetch_a, fetch_b, after])

    def fake_get(name: str):
        assert name == "worker"
        return actor

    # Mock ActorRegistry.get so the engine always retrieves our DummyActor
    monkeypatch.setattr(ActorRegistry, "get", fake_get)

    # Two steps are in the same parallel group ("fetch"), so they should run together.
    # The last step runs after the parallel group completes.
    plan = Plan(
        steps=[
            PlanStep(
                actor_name="worker",
                tool_name="fetch_a",
                parameters={},
                parallel_group="fetch",
            ),
            PlanStep(
                actor_name="worker",
                tool_name="fetch_b",
                parameters={},
                parallel_group="fetch",
            ),
            PlanStep(
                actor_name="worker",
                tool_name="after",
                parameters={},
                parallel_group=None,
            ),
        ]
    )

    engine = NativeEngine()

    # Measure total execution time to confirm concurrency
    t0 = time.perf_counter()
    ctx = await engine.execute_plan(plan, context={})
    t1 = time.perf_counter()

    elapsed = t1 - t0

    # Sequential would be ~0.55s (0.25 + 0.25 + 0.05)
    # Parallel group would be ~0.30s (max(0.25, 0.25) + 0.05)
    assert elapsed < 0.45, f"Expected parallel execution, took {elapsed:.3f}s"

    # Verify context merge from all steps
    assert ctx["a"] == 1
    assert ctx["b"] == 2
    assert ctx["after"] is True
    assert plan.status == "COMPLETED"


@pytest.mark.asyncio
async def test_parallel_group_failure_fails_group(monkeypatch):
    # This test verifies that:
    # 1) If any step inside a parallel_group fails, the entire group fails.
    # 2) The engine aborts execution and marks the plan as FAILED.
    # 3) Steps after the failed parallel group are NOT executed.

    called = {"never": False}

    async def ok():
        await asyncio.sleep(0.05)
        return {"ok": True}

    async def boom():
        await asyncio.sleep(0.05)
        raise RuntimeError("boom")

    async def never():
        called["never"] = True
        await asyncio.sleep(0.01)
        return {"never": True}

    actor = DummyActor("worker", [ok, boom, never])

    def fake_get(name: str):
        assert name == "worker"
        return actor

    monkeypatch.setattr(ActorRegistry, "get", fake_get)

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="worker",
                tool_name="ok",
                parameters={},
                parallel_group="fetch",
            ),
            PlanStep(
                actor_name="worker",
                tool_name="boom",
                parameters={},
                parallel_group="fetch",
            ),
            PlanStep(
                actor_name="worker",
                tool_name="never",
                parameters={},
                parallel_group=None,
            ),
        ]
    )

    engine = NativeEngine()

    with pytest.raises(RuntimeError) as exc:
        await engine.execute_plan(plan, context={})

    assert "Parallel group 'fetch' failed" in str(exc.value)
    assert plan.status == "FAILED"

    # IMPORTANT: confirm that "never" step did NOT run
    assert called["never"] is False
