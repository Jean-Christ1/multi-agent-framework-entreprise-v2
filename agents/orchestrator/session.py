"""Trace session helpers for orchestrator execution."""

from contextvars import ContextVar

_current_trace_id: ContextVar[str] = ContextVar("orchestrator_trace_id", default="")


def set_trace_id(trace_id: str):
    """Set the current trace identifier in context."""

    return _current_trace_id.set(trace_id)


def reset_trace_id(token):
    """Reset the current trace identifier using a token from set_trace_id."""

    if token is not None:
        _current_trace_id.reset(token)


def get_trace_id() -> str:
    """Return the trace identifier for the current execution context."""

    return _current_trace_id.get("")


__all__ = ["set_trace_id", "reset_trace_id", "get_trace_id"]
