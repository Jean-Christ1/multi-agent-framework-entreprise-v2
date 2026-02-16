from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field, ConfigDict

from framework.types import Plan
from framework.persistence.models import ProcessStatus

# ============================================================================
# Process Schema
# ============================================================================


class ProcessSchema(BaseModel):
    """
    Serialized representation of a persisted process.
    """

    id: uuid.UUID
    status: ProcessStatus
    current_plan: Plan
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Process Event Schema (JAF-27 / JAF-55)
# ============================================================================


class ProcessEventSchema(BaseModel):
    """
    Serialized representation of a persisted AgentAction event.

    Used for:
    - Process observability
    - Audit trail
    - Timeline reconstruction
    """

    id: uuid.UUID = Field(..., description="Unique event identifier")
    process_id: uuid.UUID = Field(..., description="Associated process ID")
    agent_id: str = Field(..., description="Actor / Agent identifier")
    action_type: str = Field(..., description="Type of agent action")
    message: str | None = Field(None, description="Optional human-readable message")
    status: Literal["complete", "error"] = Field(..., description="Execution status")
    created_at: datetime = Field(..., description="Event creation timestamp")

    model_config = ConfigDict(from_attributes=True)
