import asyncio
import uuid
from datetime import datetime
from typing import Callable

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from framework.persistence.database import async_session_maker, engine
from framework.persistence.models import ProcessStatus
from framework.persistence.process_repo import ProcessRepository
from framework.types import Plan, PlanStep

pytestmark = pytest.mark.asyncio

_PLAN_STATUS_MAP = {
    ProcessStatus.PENDING.value: "PLANNING",
    ProcessStatus.RUNNING.value: "EXECUTING",
    ProcessStatus.COMPLETED.value: "COMPLETED",
    ProcessStatus.FAILED.value: "FAILED",
}


def _plan_status(status: ProcessStatus | str) -> str:
    raw_status = status.value if isinstance(status, ProcessStatus) else status
    return _PLAN_STATUS_MAP.get(raw_status, raw_status)


async def _truncate_processes(session: AsyncSession) -> None:
    await session.execute(text("TRUNCATE TABLE processes"))
    await session.commit()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with async_session_maker() as session:
        try:
            await session.execute(
                text("TRUNCATE TABLE processes RESTART IDENTITY CASCADE")
            )
            await session.commit()
            yield session
        except Exception as e:
            await session.rollback()
            raise e


@pytest_asyncio.fixture(scope="session", autouse=True)
async def dispose_engine():
    """Ensure the async SQLAlchemy engine is disposed after tests complete."""
    yield
    await engine.dispose()


@pytest.fixture
def process_repo(db_session: AsyncSession) -> ProcessRepository:
    return ProcessRepository(db_session)


@pytest.fixture
def plan_factory() -> Callable[[ProcessStatus | str, int], Plan]:
    def _factory(
        status: ProcessStatus | str = ProcessStatus.PENDING,
        step_count: int = 1,
    ) -> Plan:
        steps = [
            PlanStep(
                id=f"step-{i}",
                actor_name=f"Actor-{i}",
                tool_name=f"tool-{i}",
                parameters={"cuid": f"employee-{i}"},
            )
            for i in range(step_count)
        ]
        return Plan(status=_plan_status(status), steps=steps)

    return _factory


async def test_create_save_load_process_roundtrip(
    process_repo: ProcessRepository,
    plan_factory: Callable[..., Plan],
):
    process_id = uuid.uuid4()
    initial_plan = plan_factory(status=ProcessStatus.PENDING, step_count=1)
    initial_context = {"employee": {"id": "A123", "eligible": True}}

    created = await process_repo.create_process(
        process_id,
        initial_plan,
        initial_context,
        status=ProcessStatus.PENDING,
    )

    assert created.id == process_id
    assert created.status == ProcessStatus.PENDING

    updated_plan = plan_factory(status=ProcessStatus.RUNNING, step_count=2)
    updated_context = {"result": {"score": 0.92}}

    await process_repo.save_process(process_id, updated_plan, updated_context)

    loaded_plan, loaded_context = await process_repo.load_process(process_id)
    assert loaded_plan == updated_plan
    assert loaded_context == updated_context


async def test_update_process_changes_status_and_updated_at(
    process_repo: ProcessRepository,
    plan_factory: Callable[..., Plan],
):
    process_id = uuid.uuid4()
    initial_plan = plan_factory(status=ProcessStatus.PENDING)
    created = await process_repo.create_process(
        process_id,
        initial_plan,
        {"step": 0},
        status=ProcessStatus.PENDING,
    )

    first_updated_at = created.updated_at

    await asyncio.sleep(0.01)

    new_plan = plan_factory(status=ProcessStatus.RUNNING, step_count=3)
    new_context = {"step": 2}

    updated = await process_repo.update_process(
        process_id,
        new_plan,
        new_context,
        status=ProcessStatus.RUNNING,
    )

    assert updated.status == ProcessStatus.RUNNING
    assert updated.current_plan == new_plan
    assert updated.context == new_context
    assert updated.updated_at > first_updated_at


async def test_list_processes_filters_by_status(
    process_repo: ProcessRepository,
    plan_factory: Callable[..., Plan],
):
    first_id = uuid.uuid4()
    second_id = uuid.uuid4()

    await process_repo.create_process(
        first_id,
        plan_factory(status=ProcessStatus.PENDING),
        {"employee": {"eligible": True}},
        status=ProcessStatus.PENDING,
    )

    await process_repo.create_process(
        second_id,
        plan_factory(status=ProcessStatus.RUNNING, step_count=2),
        {"employee": {"eligible": False}},
        status=ProcessStatus.RUNNING,
    )

    pending = await process_repo.list_processes(status=ProcessStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].id == first_id

    all_processes = await process_repo.list_processes()
    assert {proc.id for proc in all_processes} == {first_id, second_id}


async def test_list_processes_filters_by_date_range(
    process_repo: ProcessRepository,
    plan_factory: Callable[..., Plan],
):
    """Test that list_processes filters by date range using created_at timestamps."""
    from datetime import timezone, timedelta

    # Create processes - their created_at will be set automatically to NOW()
    first_id = uuid.uuid4()
    second_id = uuid.uuid4()
    third_id = uuid.uuid4()

    await process_repo.create_process(
        first_id,
        plan_factory(status=ProcessStatus.PENDING),
        {"employee": {"eligible": True}},
        status=ProcessStatus.PENDING,
    )

    await process_repo.create_process(
        second_id,
        plan_factory(status=ProcessStatus.RUNNING, step_count=2),
        {"employee": {"eligible": False}},
        status=ProcessStatus.RUNNING,
    )

    await process_repo.create_process(
        third_id,
        plan_factory(status=ProcessStatus.COMPLETED),
        {"employee": {"eligible": True}},
        status=ProcessStatus.COMPLETED,
    )

    # Define date range that includes today
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(hours=1)  # 1 hour ago
    to_date = now + timedelta(hours=1)  # 1 hour from now

    # Filter by date range - should return all processes created just now
    filtered = await process_repo.list_processes(from_date=from_date, to_date=to_date)
    assert len(filtered) == 3
    assert all(from_date <= process.created_at <= to_date for process in filtered)

    # Verify ordering by updated_at DESC
    assert filtered[0].updated_at >= filtered[1].updated_at
    assert filtered[1].updated_at >= filtered[2].updated_at

    # Test with date range that excludes all processes
    past_from_date = now - timedelta(days=30)
    past_to_date = now - timedelta(days=29)
    empty_filtered = await process_repo.list_processes(
        from_date=past_from_date, to_date=past_to_date
    )
    assert len(empty_filtered) == 0

    # Test with only from_date
    from_only = await process_repo.list_processes(from_date=from_date)
    assert len(from_only) == 3

    # Test with only to_date
    to_only = await process_repo.list_processes(to_date=to_date)
    assert len(to_only) == 3


async def test_load_unknown_process_raises(process_repo: ProcessRepository):
    missing_id = uuid.uuid4()
    with pytest.raises(ValueError, match=str(missing_id)):
        await process_repo.load_process(missing_id)
