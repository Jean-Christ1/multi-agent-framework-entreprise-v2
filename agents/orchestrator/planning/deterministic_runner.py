"""
Deterministic planner that leverages the existing orchestrator execution flow.
"""

from __future__ import annotations

from typing import Any, Dict

from .base import Planner
from .types import ExecutionReport, OrchestrationIntent, PlanGraph, PlannerContext


class DeterministicPlanner(Planner):
    """Simple planner that reuses the orchestrator's current execution flow."""

    name = "deterministic"

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    async def plan(
        self,
        intent: OrchestrationIntent,
        context: PlannerContext,
    ) -> PlanGraph:
        """Return a minimal plan graph describing deterministic execution."""
        metadata: Dict[str, Any] = {
            "scenario": intent.scenario,
            "planner": self.name,
        }
        return PlanGraph(
            name="deterministic-flow",
            description="Execute via orchestrator deterministic runner.",
            steps=[
                {
                    "id": "deterministic_execute",
                    "description": "Run legacy deterministic orchestration flow.",
                }
            ],
            metadata=metadata,
        )

    async def execute(
        self,
        plan: PlanGraph,
        intent: OrchestrationIntent,
        context: PlannerContext,
    ) -> ExecutionReport:
        """Execute by delegating to orchestrator deterministic flow."""
        result = await self.orchestrator._execute_deterministic_flow(
            intent=intent,
            context=context,
        )

        return ExecutionReport(
            answer=result.get("answer", ""),
            plan=plan,
            metadata=result,
            errors=result.get("errors", []),
        )
