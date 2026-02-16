import uuid
import pytest
from datetime import datetime, timezone

from framework.event_bus import Event
from framework.types import AgentAction
from framework.persistence.event_bus_subscriber import db_subscriber
from framework.persistence.database import create_session
from framework.persistence.models import (
    Process,
    ProcessStatus,
    ProcessEvent,
    ProcessEventStatus,
)


@pytest.mark.asyncio
async def test_db_subscriber_persists_agent_action():
    process_id = uuid.uuid4()

    # ------------------------------------------------------------------
    # Arrange: create a Process FIRST (FK requirement)
    # ------------------------------------------------------------------
    session = await create_session()
    try:
        process = Process(
            id=process_id,
            status=ProcessStatus.RUNNING.value,
            current_plan={},
            context={},
        )
        session.add(process)
        await session.commit()
    finally:
        await session.close()

    action = AgentAction(
        agentId="TestAgent",
        actionType="execute_step",
        message="Step executed",
        status="complete",
        error=None,
    )

    event = Event(
        name="agent_action",
        payload=action,
        process_id=process_id,
        created_at=datetime.now(tz=timezone.utc),
    )

    # ------------------------------------------------------------------
    # Act
    # ------------------------------------------------------------------
    await db_subscriber(event)

    # ------------------------------------------------------------------
    # Assert
    # ------------------------------------------------------------------
    session = await create_session()
    try:
        result = await session.execute(
            ProcessEvent.__table__.select().where(ProcessEvent.process_id == process_id)
        )
        rows = result.fetchall()
    finally:
        await session.close()

    assert len(rows) == 1

    persisted = rows[0]
    assert persisted.agent_id == "TestAgent"
    assert persisted.action_type == "execute_step"
    assert persisted.status == ProcessEventStatus.COMPLETE
