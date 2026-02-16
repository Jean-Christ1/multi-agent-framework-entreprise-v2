"""
Planner protocol and shared exceptions.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import OrchestrationIntent, PlannerContext, PlanGraph, ExecutionReport


class PlanningError(Exception):
    """Base error for planner selection or execution issues."""


@runtime_checkable
class Planner(Protocol):
    """Protocol that all planner implementations must satisfy."""

    name: str

    async def plan(
        self,
        intent: OrchestrationIntent,
        context: PlannerContext,
    ) -> PlanGraph:
        """Produce a plan graph for the provided intent."""

    async def execute(
        self,
        plan: PlanGraph,
        intent: OrchestrationIntent,
        context: PlannerContext,
    ) -> ExecutionReport:
        """Execute the supplied plan graph and return an execution report."""
