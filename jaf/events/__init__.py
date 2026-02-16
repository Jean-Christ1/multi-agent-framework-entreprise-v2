"""
JAF Events module - Backward compatibility alias.

This module provides backward compatibility for imports from jaf.events.
"""

# Re-export from framework.event_bus for backward compatibility
from framework.event_bus import (
    Event,
    EventBus,
    console_subscriber,
    get_event_bus,
)

__all__ = ["Event", "EventBus", "console_subscriber", "get_event_bus"]
