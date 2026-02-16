import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from framework.persistence.schemas import ProcessEventSchema

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_event_data():
    return {
        "id": uuid.uuid4(),
        "process_id": uuid.uuid4(),
        "agent_id": "TestAgent",
        "action_type": "execute_tool",
        "message": "Tool executed successfully",
        "status": "complete",
        "created_at": datetime.now(tz=timezone.utc),
    }


# ============================================================================
# TESTS - SUCCESS CASES
# ============================================================================


def test_process_event_schema_valid(valid_event_data):
    """Should create schema when all fields are valid."""
    event = ProcessEventSchema(**valid_event_data)

    assert event.id == valid_event_data["id"]
    assert event.process_id == valid_event_data["process_id"]
    assert event.agent_id == "TestAgent"
    assert event.action_type == "execute_tool"
    assert event.message == "Tool executed successfully"
    assert event.status == "complete"
    assert isinstance(event.created_at, datetime)


def test_process_event_schema_optional_message():
    """Message field should be optional."""
    data = {
        "id": uuid.uuid4(),
        "process_id": uuid.uuid4(),
        "agent_id": "AgentA",
        "action_type": "plan_generation",
        "status": "complete",
        "created_at": datetime.now(tz=timezone.utc),
    }

    event = ProcessEventSchema(**data)

    assert event.message is None


# ============================================================================
# TESTS - VALIDATION ERRORS
# ============================================================================


def test_process_event_schema_invalid_status():
    """Invalid status should raise ValidationError."""
    data = {
        "id": uuid.uuid4(),
        "process_id": uuid.uuid4(),
        "agent_id": "AgentA",
        "action_type": "execute",
        "status": "pending",  #  invalid
        "created_at": datetime.now(tz=timezone.utc),
    }

    with pytest.raises(ValidationError):
        ProcessEventSchema(**data)


def test_process_event_schema_missing_required_field():
    """Missing required fields should raise ValidationError."""
    data = {
        "id": uuid.uuid4(),
        # process_id missing
        "agent_id": "AgentA",
        "action_type": "execute",
        "status": "complete",
        "created_at": datetime.now(tz=timezone.utc),
    }

    with pytest.raises(ValidationError):
        ProcessEventSchema(**data)


def test_process_event_schema_invalid_uuid():
    """Invalid UUID types should be rejected."""
    data = {
        "id": "not-a-uuid",
        "process_id": uuid.uuid4(),
        "agent_id": "AgentA",
        "action_type": "execute",
        "status": "complete",
        "created_at": datetime.now(tz=timezone.utc),
    }

    with pytest.raises(ValidationError):
        ProcessEventSchema(**data)


# ============================================================================
# TESTS - ORM COMPATIBILITY
# ============================================================================


class FakeORMEvent:
    """Simulates ORM object returned from repository."""

    def __init__(self):
        self.id = uuid.uuid4()
        self.process_id = uuid.uuid4()
        self.agent_id = "ORMAgent"
        self.action_type = "evaluate_progress"
        self.message = "Progress evaluated"
        self.status = "complete"
        self.created_at = datetime.now(tz=timezone.utc)


def test_process_event_schema_from_orm():
    """Should support ORM-style objects via from_attributes."""
    orm_event = FakeORMEvent()

    event = ProcessEventSchema.model_validate(orm_event)

    assert event.agent_id == "ORMAgent"
    assert event.action_type == "evaluate_progress"
    assert event.status == "complete"
