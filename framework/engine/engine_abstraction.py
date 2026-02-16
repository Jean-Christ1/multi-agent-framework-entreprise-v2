from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from framework.actor.base_actor import Actor
from framework.types import Plan, PlanStep, StepResult, PlanUpdate


class EngineAbstraction(ABC):
    """The heart of JAF - manages the process lifecycle (planning → execution → evaluation)."""

    @abstractmethod
    async def generate_plan(self, goal: str, available_actors: List[Actor]) -> Plan:
        """
        Phase 1: PROCESS PLANNING.

        Inputs:
            goal (str): The high-level objective to accomplish.
            available_actors (List[Actor]): All actors/tools that the engine may use.

        Output:
            Plan: A fully generated Plan containing all steps required to achieve the goal.
        """
        ...

    @abstractmethod
    async def execute_step(self, step: PlanStep, context: Dict[str, Any]) -> StepResult:
        """
        Phase 2: PROCESS EXECUTION.

        Inputs:
            step (PlanStep): The step to execute.
            context (dict): Shared runtime context with intermediate results.

        Output:
            StepResult: Result of executing the step (success/error + data).
        """
        ...

    @abstractmethod
    async def evaluate_progress(self, plan: Plan, result: StepResult) -> PlanUpdate:
        """
        Phase 3: EVALUATION.

        Inputs:
            plan (Plan): Current plan being executed.
            result (StepResult): Result of the most recently executed step.

        Output:
            PlanUpdate: Engine decision: continue, modify plan, or abort process.
        """
        ...
