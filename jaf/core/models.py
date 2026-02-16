"""
JAF Core Data Models.

Re-exports shared types from framework.types and defines
additional models needed by the jaf package (ProcessState, ExecutionMode, Process).
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

# Re-export existing models from framework.types
from framework.types import LLMConfig, Plan, PlanStep, StepResult, PlanUpdate, AgentAction


# ── Enums ────────────────────────────────────────────────────────

class ProcessState(str, Enum):
    """Process lifecycle states."""
    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionMode(str, Enum):
    """Supported execution modes."""
    AGENTIC = "agentic"
    MULTI_AGENT = "multi_agent"
    TRADITIONAL = "traditional"


class ActionType(str, Enum):
    """Post-evaluation actions."""
    CONTINUE = "continue"
    MODIFY = "modify"
    ABORT = "abort"
    COMPLETE = "complete"


# ── Process Model ────────────────────────────────────────────────

class NextAction(BaseModel):
    """Decision returned by engine.evaluate()."""
    action: ActionType = ActionType.CONTINUE
    reason: str = ""


class Process(BaseModel):
    """A running process tracked by the engine."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str = ""
    state: ProcessState = ProcessState.CREATED
    mode: ExecutionMode = ExecutionMode.AGENTIC
    context: Dict[str, Any] = Field(default_factory=dict)
    plan: Optional[Plan] = None
    results: List[StepResult] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def transition_to(self, new_state: ProcessState) -> None:
        self.state = new_state
        if new_state in (ProcessState.COMPLETED, ProcessState.FAILED):
            self.completed_at = datetime.utcnow()

    def add_result(self, result: StepResult) -> None:
        self.results.append(result)

    @property
    def duration_ms(self) -> int:
        if self.completed_at and self.created_at:
            return int((self.completed_at - self.created_at).total_seconds() * 1000)
        return 0

    @property
    def total_tokens(self) -> int:
        return 0  # placeholder

    @property
    def is_terminal(self) -> bool:
        return self.state in (ProcessState.COMPLETED, ProcessState.FAILED)


__all__ = [
    "LLMConfig", "Plan", "PlanStep", "StepResult", "PlanUpdate", "AgentAction",
    "ProcessState", "ExecutionMode", "ActionType", "NextAction", "Process",
]
