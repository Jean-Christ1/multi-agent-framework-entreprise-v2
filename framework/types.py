"""
Pydantic models for the JAF framework.

Tickets: JAF-4, JAF-17, JAF-29
"""

from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid
from uuid import UUID


class LLMConfig(BaseModel):
    """
    Configuration for an LLM used by an Actor.

    Supports:
    - Model selection (any model string accepted; validation is upstream)
    - Temperature control (0.0 to 2.0)
    - Max token limit (optional)

    Usage:
        llm_config = None          # deterministic actor (no LLM)
        llm_config = LLMConfig(...) # probabilistic actor (uses LLM)
    """

    model: str = Field(
        ..., description="Model name (e.g., gpt-4o, gpt-4o-mini, claude-3-opus)"
    )

    temperature: float = Field(
        0.0, ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)"
    )

    max_tokens: Optional[int] = Field(
        None, gt=0, description="Max number of tokens to generate"
    )

    model_config = ConfigDict(frozen=True)


class PlanStep(BaseModel):
    """A single step in an execution plan."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    actor_name: str
    tool_name: str
    parameters: Dict[str, Any]
    status: Literal["pending", "executing", "completed", "failed"] = "pending"

    # Parallel execution support
    parallel_group: Optional[str] = None


# Mermaid node colors by step status (flowchart style)
_PLAN_MERMAID_STATUS_COLORS = {
    "pending": "#e0e0e0",
    "executing": "#bbdefb",
    "completed": "#c8e6c9",
    "failed": "#ffcdd2",
}


class Plan(BaseModel):
    """Execution plan containing multiple steps."""

    steps: List[PlanStep]
    status: Literal["PLANNING", "EXECUTING", "COMPLETED", "FAILED"] = "PLANNING"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def next_step(self) -> Optional[PlanStep]:
        """Return the next pending step, or None if all complete."""
        for step in self.steps:
            if step.status == "pending":
                return step
        return None

    def to_mermaid(self) -> str:
        """
        Generate a Mermaid flowchart string for this plan.

        - One node per step, labeled as actor_name.tool_name.
        - Consecutive steps with the same parallel_group are shown as parallel branches.
        - Node fill color reflects step status: pending (gray), executing (blue),
          completed (green), failed (red).

        Returns:
            Valid Mermaid flowchart string (flowchart TD).
        """
        if not self.steps:
            return "flowchart TD\n  empty((empty plan))"

        node_ids: List[str] = []
        node_defs: List[str] = []
        style_defs: List[str] = []
        for i, step in enumerate(self.steps):
            nid = f"s{i}"
            node_ids.append(nid)
            label = f"{step.actor_name}.{step.tool_name}".replace('"', '""')
            node_defs.append(f'  {nid}["{label}"]')
            color = _PLAN_MERMAID_STATUS_COLORS.get(step.status, "#e0e0e0")
            style_defs.append(f"  style {nid} fill:{color}")

        # Partition steps into blocks: sequential single step, or maximal run with same parallel_group
        blocks: List[List[int]] = []
        idx = 0
        while idx < len(self.steps):
            step = self.steps[idx]
            pg = step.parallel_group
            if pg is None:
                blocks.append([idx])
                idx += 1
            else:
                block = [idx]
                idx += 1
                while idx < len(self.steps) and self.steps[idx].parallel_group == pg:
                    block.append(idx)
                    idx += 1
                blocks.append(block)

        # Edges: from every node in block k to every node in block k+1
        edge_defs: List[str] = []
        for b in range(len(blocks) - 1):
            for fi in blocks[b]:
                for ti in blocks[b + 1]:
                    edge_defs.append(f"  {node_ids[fi]} --> {node_ids[ti]}")

        out_lines = ["flowchart TD"] + node_defs + edge_defs + style_defs
        return "\n".join(out_lines)


class StepResult(BaseModel):
    """Result of executing a single plan step."""

    output: Dict[str, Any]
    status: Literal["success", "error"]
    error: Optional[str] = None
    execution_time: float = 0.0
    cost: float = 0.0


class PlanUpdate(BaseModel):
    """Update decision after evaluating step progress."""

    action: Literal["continue", "modify", "retry", "abort"]
    modified_plan: Optional[Plan] = None
    reason: str


class AgentAction(BaseModel):
    """
    Event representing an agent action.

    Fields match Sprint 1 spec:
    - agentId: Actor identifier
    - actionType: Type of action performed
    - message: Human-readable description
    - status: "complete" or "error"
    - timestamp: ISO 8601 string with Z suffix
    """

    agentId: str
    actionType: str
    message: str
    status: Literal["complete", "error"]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class LLMTelemetry(BaseModel):
    """
    Telemetry record for a single LLM call.

    This model is persisted in the `llm_telemetry` table and represents
    the minimal observability unit for cost, latency and usage tracking.
    """

    process_id: UUID
    actor_name: str

    engine: str  # e.g. "crewai", "native"
    model: str

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)

    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
