"""
Event Bus for the JAF framework.

Ticket: JAF-28

Provides a simple publish/subscribe mechanism for broadcasting AgentAction
events during execution. Supports both synchronous (emit) and asynchronous
(publish) subscribers. Subscriber errors are isolated and logged.
"""

import asyncio
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Union

from framework.types import AgentAction
from framework.logging import get_logger

logger = get_logger("event_bus")


@dataclass
class Event:
    """Event wrapper for async subscribers."""

    name: str
    payload: Any
    created_at: datetime
    process_id: uuid.UUID | None = None


Subscriber = Callable[[Union[AgentAction, Dict[str, Any], Event]], Any]


class EventBus:
    """
    Thread-safe singleton Event Bus for broadcasting AgentAction events.
    """

    _instance: "EventBus | None" = None
    _lock = threading.Lock()
    _subscribers: List[Subscriber]
    _subscribers_lock: threading.Lock

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._subscribers = []
                    instance._subscribers_lock = threading.Lock()
                    cls._instance = instance
        return cls._instance

    def emit(self, action: Union[AgentAction, Dict[str, Any]]) -> None:
        """
        Emit event to all subscribers (synchronous).
        """
        if isinstance(action, dict):
            process_id = action.get("process_id")
            action_type = action.get("actionType", "unknown")
        else:
            process_id = getattr(action, "process_id", None)
            action_type = getattr(action, "actionType", "unknown")

        event = Event(
            name=action_type,
            payload=action,
            created_at=datetime.now(timezone.utc),
            process_id=process_id,
        )

        self._dispatch(event)

    async def publish(self, event: Event) -> None:
        """
        Publish event to all subscribers (asynchronous).
        """
        self._dispatch(event)

    def _dispatch(self, event: Event) -> None:
        with self._subscribers_lock:
            subscribers = self._subscribers.copy()

        for subscriber in subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    asyncio.create_task(subscriber(event))
                else:
                    try:
                        subscriber(event.payload)
                    except (TypeError, AttributeError):
                        subscriber(event)
            except Exception:
                logger.warning("Subscriber error", exc_info=True)

    def subscribe(self, callback: Subscriber) -> None:
        with self._subscribers_lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        with self._subscribers_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def clear(self) -> None:
        with self._subscribers_lock:
            self._subscribers.clear()


def get_event_bus() -> EventBus:
    return EventBus()


def console_subscriber(action: Union[AgentAction, Dict[str, Any], Event]) -> None:
    """
    Built-in subscriber that logs events using structured logging.
    """
    if isinstance(action, Event):
        payload = action.payload

        if isinstance(payload, dict):
            agent_id = payload.get("agentId", "-")
            status = payload.get("status", "-")
            event_msg = payload.get("message", "")
        else:
            agent_id = getattr(payload, "agentId", "-")
            status = getattr(payload, "status", "-")
            event_msg = getattr(payload, "message", "")

        logger.info(f"[{action.name}] agent={agent_id} status={status} | {event_msg}")
        return

    if isinstance(action, dict):
        agent_id = action.get("agentId", "-")
        status = action.get("status", "-")
        event_msg = action.get("message", "")
        action_type = action.get("actionType", "unknown")
    else:
        agent_id = getattr(action, "agentId", "-")
        status = getattr(action, "status", "-")
        event_msg = getattr(action, "message", "")
        action_type = getattr(action, "actionType", "unknown")

    logger.info(f"[{action_type}] agent={agent_id} status={status} | {event_msg}")
