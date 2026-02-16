"""
Framework-level exceptions.

All custom exceptions used across JAF must inherit from FrameworkException.
"""


class FrameworkException(Exception):
    """Base exception for the JAF framework."""

    pass


class EngineException(FrameworkException):
    """Raised when an engine (planning, execution, evaluation) fails."""

    pass
