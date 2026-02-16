"""
EventBus Flow Example

Demonstrates EventBus capabilities with AgentAction events.

Demo covers:
1. Broadcast - multiple subscribers receive same event
2. Error isolation - failing subscriber doesn't break others
3. Subscribe/unsubscribe works
4. Payload is AgentAction (typed, not ad-hoc dict)

Usage:
    python examples/event_bus_flow.py
"""

from framework.event_bus import get_event_bus
from framework.types import AgentAction


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def demo_broadcast():
    """Two subscribers both receive the same AgentAction."""
    print_header("1: Broadcast - Multiple Subscribers")

    bus = get_event_bus()
    bus.clear()

    # Two different subscribers
    bus.subscribe(
        lambda e: print(
            f"  [SUBSCRIBER 1] Received: {e.actionType} (type: {type(e).__name__})"
        )
    )
    bus.subscribe(lambda e: print(f"  [SUBSCRIBER 2] Received: {e.actionType}"))

    print("Emitting ONE AgentAction event...\n")

    bus.emit(
        AgentAction(
            agentId="TestActor",
            actionType="user_created",
            message="Created user john@example.com",
            status="complete",
        )
    )

    print("\n✅ Both subscribers received the same event!")
    bus.clear()


def demo_error_isolation():
    """2: One subscriber throws, the other still receives."""
    print_header("2: Error Isolation - Failing Subscriber")

    bus = get_event_bus()
    bus.clear()

    # First good subscriber
    bus.subscribe(lambda e: print(f"  [GOOD 1] ✅ Received: {e.actionType}"))

    # Bad subscriber that crashes
    def bad_subscriber(e):
        raise Exception("I crashed!")

    bus.subscribe(bad_subscriber)

    # Second good subscriber
    bus.subscribe(lambda e: print(f"  [GOOD 2] ✅ Received: {e.actionType}"))

    print("Emitting event (middle subscriber will CRASH)...\n")

    bus.emit(
        AgentAction(
            agentId="Test",
            actionType="test_event",
            message="Testing error isolation",
            status="complete",
        )
    )

    bus.clear()


def demo_subscribe_unsubscribe():
    """3: Subscribe and unsubscribe works correctly."""
    print_header("3: Subscribe / Unsubscribe")

    bus = get_event_bus()
    bus.clear()

    def callback(e):
        print(f"  [CALLBACK] Received: {e.actionType}")

    print("1. Subscribe and emit:")
    bus.subscribe(callback)
    bus.emit(
        AgentAction(
            agentId="Test",
            actionType="first_event",
            message="First event",
            status="complete",
        )
    )

    print("\n2. Unsubscribe and emit:")
    bus.unsubscribe(callback)
    bus.emit(
        AgentAction(
            agentId="Test",
            actionType="second_event",
            message="Second event (should not print)",
            status="complete",
        )
    )

    print("  (no output)")
    bus.clear()


def main():
    print("\n")
    print("JAF-28: Event Bus Implementation")

    demo_broadcast()
    demo_error_isolation()
    demo_subscribe_unsubscribe()

    print(
        """
    SUMMARY:
    ✅ Broadcast: Multiple subscribers receive same event
    ✅ Error Isolation: Failing subscribers don't break others
    ✅ Subscribe/Unsubscribe: Works correctly
    """
    )


if __name__ == "__main__":
    main()
