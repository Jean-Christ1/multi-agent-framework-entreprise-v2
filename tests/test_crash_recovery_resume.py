"""
Test: crash recovery + resume (kill mid-run, restart orchestrator, resume completes).

Prerequisites:
1) Make sure the Postgres container used by the tests is running (container: 'jaf-postgres'):
   - docker ps
   - docker start jaf-postgres
   - docker port jaf-postgres
   - docker logs jaf-postgres --tail 50

2) Ensure the test configuration points to that database
   (e.g. DATABASE_URL / test config / session_maker fixture).

How to run this test:
   pytest ./tests/test_crash_recovery_resume.py -v -s --log-cli-level=INFO
"""

import asyncio
import uuid
import pytest
from unittest.mock import Mock

from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry
from framework.engine.native_engine import NativeEngine
from framework.orchestrator import Orchestrator
from framework.persistence.models import ProcessStatus
from framework.persistence.process_repo import ProcessRepository
from framework.types import Plan, PlanStep
from framework.event_bus import EventBus


class CrashActor(Actor):
    def configure(self) -> None:
        self.name = "CrashActor"
        self.description = "Crash recovery test actor"
        self.goal = "Test crash recovery"
        self.llm_config = None
        self.utilities = []
        self.tools = [self.step1, self.step2, self.step3]

    async def step1(self) -> str:
        return "ok1"

    async def step2(self) -> str:
        await asyncio.sleep(2)
        return "ok2"

    async def step3(self) -> str:
        return "ok3"


@pytest.mark.asyncio
async def test_kill_mid_run_restart_resume_completes(session_maker):
    # --- setup actors ---
    ActorRegistry.clear()
    ActorRegistry.register("CrashActor", CrashActor)

    plan = Plan(
        steps=[
            PlanStep(
                actor_name="CrashActor",
                tool_name="step1",
                parameters={},
                status="pending",
            ),
            PlanStep(
                actor_name="CrashActor",
                tool_name="step2",
                parameters={},
                status="pending",
            ),
            PlanStep(
                actor_name="CrashActor",
                tool_name="step3",
                parameters={},
                status="pending",
            ),
        ],
        status="PLANNING",
    )

    engine = NativeEngine(default_plan=plan)
    orch = Orchestrator(engine=engine, session_maker=session_maker)

    process_id = uuid.uuid4()

    # --- start run in background ---
    task = asyncio.create_task(
        orch.run(
            goal="test crash recovery",
            actors=[CrashActor()],
            process_id=process_id,
        )
    )

    # --- wait until step2 becomes "executing" ---
    async with session_maker() as session:
        repo = ProcessRepository(session)

        found = False
        for _ in range(200):  # max ~10s
            try:
                proc = await repo.get_process(process_id)
            except ValueError:
                await asyncio.sleep(0.05)
                continue

            if (
                len(proc.current_plan.steps) >= 2
                and proc.current_plan.steps[1].status == "executing"
            ):
                found = True
                break

            await asyncio.sleep(0.05)

        assert found, "Step2 never reached 'executing' state"

    # --- simulate crash ---
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # --- restart + resume with mock event bus ---
    mock_event_bus = Mock(spec=EventBus)
    orch2 = Orchestrator(
        engine=engine, session_maker=session_maker, event_bus=mock_event_bus
    )
    result = await orch2.resume(process_id)

    # --- assertions ---
    assert result.status == ProcessStatus.COMPLETED
    assert result.plan.status == "COMPLETED"
    assert all(step.status == "completed" for step in result.plan.steps)

    # --- verify process_resumed event was emitted ---
    assert mock_event_bus.emit.call_count > 0, "No events were emitted"

    # emit() may receive AgentAction or dict; handle both safely
    emitted = [call.args[0] for call in mock_event_bus.emit.call_args_list if call.args]
    process_resumed_emitted = any(
        (getattr(evt, "actionType", None) == "process_resumed")
        or (isinstance(evt, dict) and evt.get("actionType") == "process_resumed")
        for evt in emitted
    )

    assert process_resumed_emitted, "process_resumed event should be emitted"
