from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from framework.event_bus import Event
from framework.types import AgentAction
from framework.persistence.database import create_session
from framework.persistence.models import ProcessEvent, ProcessEventStatus
from framework.logging import get_logger

logger = get_logger(__name__)


async def db_subscriber(event: Event) -> None:
    """
    Persist AgentAction events to the database.
    Must NEVER break execution.
    """

    if not isinstance(event.payload, AgentAction):
        return

    if event.process_id is None:
        logger.warning("AgentAction event without process_id – skipped")
        return

    action: AgentAction = event.payload

    try:
        session: AsyncSession = await create_session()
        try:
            await _persist_action(session, event.process_id, action)
        finally:
            await session.close()

    except Exception:
        logger.exception("Failed to persist AgentAction event")


async def _persist_action(
    session: AsyncSession,
    process_id: uuid.UUID,
    action: AgentAction,
) -> None:
    data = action.model_dump(by_alias=True)

    # IMPORTANT: use .value (lowercase) for PostgreSQL ENUM
    status_value = (
        ProcessEventStatus.ERROR.value
        if data.get("error")
        else ProcessEventStatus.COMPLETE.value
    )

    event = ProcessEvent(
        id=uuid.uuid4(),
        process_id=process_id,
        agent_id=data["agentId"],
        action_type=data["actionType"],
        message=data.get("message"),
        status=status_value,  #
        created_at=datetime.now(tz=timezone.utc),
    )

    session.add(event)
    await session.commit()
