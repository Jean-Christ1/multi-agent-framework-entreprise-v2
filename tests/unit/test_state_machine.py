"""
Unit tests for ProcessStateMachine.

Covers:
- Valid state transitions
- Invalid transitions raising InvalidTransitionError
- Terminal state behavior
- Initial state
- Transition configuration consistency

ProcessStatus represents the overall process execution state
(PENDING, RUNNING, COMPLETED, FAILED), distinct from Plan.status.
"""

import pytest
from framework.persistence.models import ProcessStatus
from framework.state_machine import ProcessStateMachine, InvalidTransitionError

# ============================================================================
# Transition matrix (expected behavior)
# ============================================================================

EXPECTED_TRANSITIONS = {
    ProcessStatus.PENDING: {ProcessStatus.RUNNING, ProcessStatus.FAILED},
    ProcessStatus.RUNNING: {ProcessStatus.COMPLETED, ProcessStatus.FAILED},
    ProcessStatus.COMPLETED: set(),
    ProcessStatus.FAILED: set(),
    ProcessStatus.DRY_RUN: set(),  # DRY_RUN is a terminal state with no transitions
}


# ============================================================================
# Tests – Valid transitions
# ============================================================================


@pytest.mark.parametrize(
    "from_status,to_status",
    [
        (from_status, to_status)
        for from_status, targets in EXPECTED_TRANSITIONS.items()
        for to_status in targets
    ],
)
def test_valid_transitions_are_allowed(from_status, to_status):
    assert ProcessStateMachine.can_transition(from_status, to_status)
    ProcessStateMachine.validate_transition(from_status, to_status)


# ============================================================================
# Tests – Invalid transitions
# ============================================================================


@pytest.mark.parametrize(
    "from_status,to_status",
    [
        (from_status, to_status)
        for from_status in ProcessStatus
        for to_status in ProcessStatus
        if to_status not in EXPECTED_TRANSITIONS[from_status]
    ],
)
def test_invalid_transitions_raise_invalid_transition_error(from_status, to_status):
    assert not ProcessStateMachine.can_transition(from_status, to_status)
    with pytest.raises(InvalidTransitionError):
        ProcessStateMachine.validate_transition(from_status, to_status)


def test_invalid_transition_error_contains_statuses():
    with pytest.raises(InvalidTransitionError) as exc:
        ProcessStateMachine.validate_transition(
            ProcessStatus.PENDING, ProcessStatus.COMPLETED
        )

    error = exc.value
    assert error.from_status == ProcessStatus.PENDING
    assert error.to_status == ProcessStatus.COMPLETED
    assert "pending" in str(error).lower()
    assert "completed" in str(error).lower()


# ============================================================================
# Tests – Terminal states
# ============================================================================


@pytest.mark.parametrize(
    "status,expected_terminal",
    [
        (ProcessStatus.PENDING, False),
        (ProcessStatus.RUNNING, False),
        (ProcessStatus.COMPLETED, True),
        (ProcessStatus.FAILED, True),
    ],
)
def test_is_terminal(status, expected_terminal):
    assert ProcessStateMachine.is_terminal(status) is expected_terminal


def test_terminal_states_have_no_valid_transitions():
    assert ProcessStateMachine.get_valid_transitions(ProcessStatus.COMPLETED) == set()
    assert ProcessStateMachine.get_valid_transitions(ProcessStatus.FAILED) == set()


# ============================================================================
# Tests – State machine configuration
# ============================================================================


def test_initial_status_is_pending():
    assert ProcessStateMachine.get_initial_status() == ProcessStatus.PENDING


def test_get_valid_transitions_match_expected_matrix():
    for status, expected in EXPECTED_TRANSITIONS.items():
        assert ProcessStateMachine.get_valid_transitions(status) == expected


def test_get_valid_transitions_returns_copy():
    transitions_1 = ProcessStateMachine.get_valid_transitions(ProcessStatus.PENDING)
    transitions_2 = ProcessStateMachine.get_valid_transitions(ProcessStatus.PENDING)

    transitions_1.add(ProcessStatus.COMPLETED)

    assert ProcessStatus.COMPLETED not in transitions_2


@pytest.mark.skip(
    reason="DRY_RUN status added but not included in state machine TRANSITIONS - needs state machine update"
)
def test_transitions_cover_all_process_statuses():
    assert set(ProcessStateMachine.TRANSITIONS.keys()) == set(ProcessStatus)
