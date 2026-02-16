"""
Process State Machine for JAF framework.

Manages valid state transitions for process execution.
"""

from __future__ import annotations

from typing import Set

from framework.persistence.models import ProcessStatus
from framework.logging import get_logger

logger = get_logger(__name__)


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_status: ProcessStatus, to_status: ProcessStatus):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid transition from {from_status.value} to {to_status.value}"
        )


class ProcessStateMachine:
    """
    Manages process state transitions with validation.

    State Diagram:
        PENDING ──┬──> RUNNING ──┬──> COMPLETED
                  │              │
                  └──> FAILED <──┘

    Terminal states: COMPLETED, FAILED
    """

    # Valid transitions: from_status -> set of valid to_statuses
    TRANSITIONS: dict[ProcessStatus, Set[ProcessStatus]] = {
        ProcessStatus.PENDING: {ProcessStatus.RUNNING, ProcessStatus.FAILED},
        ProcessStatus.RUNNING: {ProcessStatus.COMPLETED, ProcessStatus.FAILED},
        ProcessStatus.COMPLETED: set(),  # Terminal state
        ProcessStatus.FAILED: set(),  # Terminal state
    }

    @classmethod
    def can_transition(
        cls,
        from_status: ProcessStatus,
        to_status: ProcessStatus,
    ) -> bool:
        """
        Check if a state transition is valid.

        Args:
            from_status: Current process status
            to_status: Desired new status

        Returns:
            True if transition is valid, False otherwise
        """
        valid_targets = cls.TRANSITIONS.get(from_status, set())
        return to_status in valid_targets

    @classmethod
    def validate_transition(
        cls,
        from_status: ProcessStatus,
        to_status: ProcessStatus,
    ) -> None:
        """
        Validate a state transition, raising if invalid.

        Args:
            from_status: Current process status
            to_status: Desired new status

        Raises:
            InvalidTransitionError: If transition is not allowed
        """
        if not cls.can_transition(from_status, to_status):
            raise InvalidTransitionError(from_status, to_status)

    @classmethod
    def is_terminal(cls, status: ProcessStatus) -> bool:
        """
        Check if a status is terminal (no further transitions allowed).

        Args:
            status: Process status to check

        Returns:
            True if status is terminal (COMPLETED or FAILED)
        """
        return len(cls.TRANSITIONS.get(status, set())) == 0

    @classmethod
    def get_valid_transitions(cls, status: ProcessStatus) -> Set[ProcessStatus]:
        """
        Get all valid target statuses from a given status.

        Args:
            status: Current process status

        Returns:
            Set of valid target statuses
        """
        return cls.TRANSITIONS.get(status, set()).copy()

    @classmethod
    def get_initial_status(cls) -> ProcessStatus:
        """Return the initial status for new processes."""
        return ProcessStatus.PENDING
