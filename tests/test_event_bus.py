"""
Unit tests for EventBus core contract.

Ticket: JAF-28

Tests covered:
    1. Broadcast - all subscribers receive events
    2. Unsubscribe - removed subscribers don't receive events
    3. Error isolation - one failing subscriber doesn't break others
    4. Singleton pattern - single instance across application
    5. Duplicate subscription is prevented
    6. Console subscriber works without errors
    7. Console subscriber handles events with missing fields
    8. Works with AgentAction objects
"""

import uuid
import pytest

from framework.event_bus import EventBus, get_event_bus, console_subscriber
from framework.types import AgentAction


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    EventBus._instance = None
    yield
    EventBus._instance = None


def test_broadcast_to_all_subscribers():
    """All subscribers should receive the same event."""
    bus = get_event_bus()
    received_1 = []
    received_2 = []
    received_3 = []

    bus.subscribe(lambda e: received_1.append(e))
    bus.subscribe(lambda e: received_2.append(e))
    bus.subscribe(lambda e: received_3.append(e))

    event = AgentAction(
        agentId="test-agent",
        actionType="test_action",
        message="Test message",
        status="complete",
    )
    bus.emit(event)

    assert len(received_1) == 1
    assert len(received_2) == 1
    assert len(received_3) == 1
    assert received_1[0] == event
    assert received_2[0] == event
    assert received_3[0] == event


def test_unsubscribe_stops_receiving():
    """Unsubscribed callbacks should not receive events."""
    bus = get_event_bus()
    received = []

    def callback(e):
        received.append(e)

    bus.subscribe(callback)

    bus.emit(
        AgentAction(
            agentId="agent-1",
            actionType="first_event",
            message="First",
            status="complete",
        )
    )

    bus.unsubscribe(callback)

    bus.emit(
        AgentAction(
            agentId="agent-1",
            actionType="second_event",
            message="Second",
            status="complete",
        )
    )

    assert len(received) == 1
    assert received[0].actionType == "first_event"


def test_error_isolation():
    """One failing subscriber should not break others."""
    bus = get_event_bus()
    received_before = []
    received_after = []

    def failing_subscriber(e):
        raise Exception("I crashed!")

    bus.subscribe(lambda e: received_before.append(e))
    bus.subscribe(failing_subscriber)
    bus.subscribe(lambda e: received_after.append(e))

    event = AgentAction(
        agentId="test-agent",
        actionType="test",
        message="Test",
        status="complete",
    )
    bus.emit(event)  # Should not raise

    # Both working subscribers should still receive the event
    assert len(received_before) == 1
    assert len(received_after) == 1


def test_singleton():
    """get_event_bus() should always return the same instance."""
    bus1 = get_event_bus()
    bus2 = get_event_bus()
    bus3 = EventBus()

    assert bus1 is bus2
    assert bus2 is bus3


def test_duplicate_subscription_prevented():
    """Same callback should not be added multiple times."""
    bus = get_event_bus()
    received = []

    def callback(e):
        received.append(e)

    bus.subscribe(callback)
    bus.subscribe(callback)  # Duplicate
    bus.subscribe(callback)  # Duplicate

    bus.emit(
        AgentAction(
            agentId="agent-1",
            actionType="test",
            message="Test",
            status="complete",
        )
    )

    # Should only receive once despite multiple subscribe calls
    assert len(received) == 1


def test_console_subscriber_with_agent_action():
    """Console subscriber should work with AgentAction objects."""
    bus = get_event_bus()
    bus.subscribe(console_subscriber)

    bus.emit(
        AgentAction(
            agentId="console-test",
            actionType="test_action",
            message="Testing console output",
            status="complete",
        )
    )

    # No exception = pass
    bus.unsubscribe(console_subscriber)


def test_console_subscriber_with_dict():
    """Console subscriber should work with dict events."""
    bus = get_event_bus()
    bus.subscribe(console_subscriber)

    bus.emit(
        {
            "agentId": "dict-test",
            "actionType": "dict_action",
            "message": "Dict message",
            "status": "complete",
        }
    )

    # No exception = pass
    bus.unsubscribe(console_subscriber)


def test_console_subscriber_handles_missing_fields():
    """Console subscriber should handle events with missing fields gracefully."""
    bus = get_event_bus()
    bus.subscribe(console_subscriber)

    bus.emit({"actionType": "minimal_event"})
    bus.emit({})  # Empty dict

    # No exception = pass
    bus.unsubscribe(console_subscriber)


def test_clear_removes_all_subscribers():
    """clear() should remove all subscribers."""
    bus = get_event_bus()
    received = []

    bus.subscribe(lambda e: received.append(e))
    bus.subscribe(lambda e: received.append(e))
    bus.clear()

    bus.emit(
        AgentAction(
            agentId="test",
            actionType="test",
            message="Test",
            status="complete",
        )
    )

    assert len(received) == 0


def test_console_subscriber_logs_without_error():
    """Console subscriber should log events without errors."""
    from framework.event_bus import console_subscriber, Event
    from datetime import datetime, timezone

    test_process_id = uuid.uuid4()
    event = Event(
        name="test",
        payload={"message": "hi"},
        created_at=datetime.now(timezone.utc),
        process_id=test_process_id,
    )

    # Should not raise
    console_subscriber(event)
