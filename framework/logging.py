import logging
import os
import json
from typing import Dict, Optional, Any
from datetime import datetime
import contextvars

# ============================================================
# Context variables (safe for async / concurrent execution)
# ============================================================

_process_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "process_id", default=None
)
_actor_name: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "actor_name", default=None
)
_step_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "step_id", default=None
)

# Cache only base loggers (NOT adapters)
_LOGGERS: Dict[str, logging.Logger] = {}


# ============================================================
# Sentinel for explicit context clearing
# ============================================================


class _UnsetType:
    """Sentinel type to distinguish between 'not provided' and 'explicitly None'."""

    def __repr__(self):
        return "_UNSET"


_UNSET = _UnsetType()


# ============================================================
# Context management API
# ============================================================


def set_logging_context(
    *,
    process_id: Optional[Any] = _UNSET,
    actor_name: Optional[Any] = _UNSET,
    step_id: Optional[Any] = _UNSET,
) -> None:
    """
    Set or update the logging context for the current execution scope.
    Safe for concurrent and async usage.

    Args:
        process_id: Process ID to set, or None to clear, or _UNSET (default) to leave unchanged
        actor_name: Actor name to set, or None to clear, or _UNSET (default) to leave unchanged
        step_id: Step ID to set, or None to clear, or _UNSET (default) to leave unchanged

    Examples:
        set_logging_context(process_id="proc-1")  # Set process_id
        set_logging_context(actor_name="ActorA")  # Set actor_name, keep process_id
        set_logging_context(actor_name=None)      # Clear actor_name, keep process_id
    """
    if process_id is not _UNSET:
        _process_id.set(None if process_id is None else str(process_id))
    if actor_name is not _UNSET:
        _actor_name.set(None if actor_name is None else str(actor_name))
    if step_id is not _UNSET:
        _step_id.set(None if step_id is None else str(step_id))


# ============================================================
# Formatter
# ============================================================


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "process_id": _process_id.get(),
            "actor_name": _actor_name.get(),
            "step_id": _step_id.get(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Merge extra fields from record.__dict__ that aren't reserved
        reserved_keys = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "timestamp",
            "level",
            "logger",
            "process_id",
            "actor_name",
            "step_id",
            "exception",
        }

        for key, value in record.__dict__.items():
            if key not in reserved_keys and not key.startswith("_"):
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


# ============================================================
# Logger adapter
# ============================================================


class ContextLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        # No per-call context mutation, context is read dynamically
        return msg, kwargs


# ============================================================
# Public logger factory
# ============================================================


def get_logger(name: str) -> logging.LoggerAdapter:
    """
    Return a framework logger with structured / readable output
    and automatic context injection.

    The context (process_id, actor_name, step_id) is resolved dynamically
    via contextvars at log time.
    """
    if name not in _LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not logger.handlers:
            handler = logging.StreamHandler()

            if os.getenv("LOG_FORMAT") == "json":
                formatter = JSONFormatter()
            else:
                formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                )

            handler.setFormatter(formatter)
            logger.addHandler(handler)

        _LOGGERS[name] = logger

    return ContextLoggerAdapter(_LOGGERS[name], {})
