"""
CrewAI planner adapter leveraging native planning features.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List

from crewai import Crew, Process, Task

from .base import Planner
from .types import ExecutionReport, OrchestrationIntent, PlanGraph, PlannerContext
from ..utils import get_trace_session


class CrewAIPlanner(Planner):
    """Planner that delegates execution to CrewAI's planning engine."""

    name = "crewai"

    def __init__(self, orchestrator: Any):
        self.orchestrator = orchestrator

    async def plan(
        self,
        intent: OrchestrationIntent,
        context: PlannerContext,
    ) -> PlanGraph:
        """Generate a plan graph based on policy metadata or discovered agents."""
        policy_payload = intent.metadata.get("policy") if intent.metadata else None
        steps: List[Dict[str, Any]] = []
        description_parts: List[str] = [
            "CrewAI hierarchical planning with dynamic agent delegation."
        ]

        if policy_payload:
            workflow = policy_payload.get("workflow", {})
            steps = workflow.get("steps", [])
            summary = workflow.get("summary")
            if summary:
                description_parts.append(f"Policy summary: {summary}")
        else:
            for agent in context.discovery.get("agents", []):
                steps.append(
                    {
                        "agent": agent.get("name"),
                        "description": agent.get("description"),
                        "tool_count": agent.get("tool_count"),
                    }
                )
            description_parts.append("Steps inferred from discovered agents.")

        return PlanGraph(
            name="crewai-hierarchical-plan",
            description=" ".join(description_parts),
            steps=steps,
            metadata={
                "planner": self.name,
                "scenario": intent.scenario,
                "policy_version": (
                    intent.metadata.get("policy_version") if intent.metadata else None
                ),
            },
        )

    async def execute(
        self,
        plan: PlanGraph,
        intent: OrchestrationIntent,
        context: PlannerContext,
    ) -> ExecutionReport:
        """Execute plan using CrewAI planner with planning enabled."""
        user_prompt = intent.prompt
        step_callback = context.step_callback
        trace_id = context.trace_id or ""
        policy_payload = intent.metadata.get("policy") if intent.metadata else None
        discovery_info = (
            context.discovery or self.orchestrator.discover_agents_enhanced()
        )
        start_time = (
            datetime.fromtimestamp(context.start_time_ms / 1000.0)
            if context.start_time_ms
            else datetime.now()
        )

        agents_summary = []
        for agent in discovery_info.get("agents", []):
            agent_name = agent.get("name", "Unknown")
            tool_count = agent.get("tool_count", 0)
            agents_summary.append(f"  • {agent_name} ({tool_count} tools)")
        discovery_context = (
            "\n\n### AVAILABLE AGENTS\n" + "\n".join(agents_summary)
            if agents_summary
            else ""
        )

        policy_context = ""
        if policy_payload:
            summary = policy_payload.get("workflow", {}).get("summary")
            if summary:
                scenario_label = (
                    policy_payload.get("metadata", {})
                    .get("scenario", intent.scenario or "policy")
                    .upper()
                )
                policy_context = (
                    f"\n\n### POLICY WORKFLOW SUMMARY ({scenario_label})\n{summary}\n"
                )

        execution_task_description = f"""
            USER REQUEST: {user_prompt}

            Use CrewAI's planning to coordinate specialized agents and tools.

            CRITICAL RULES:
            1. Delegate subtasks to appropriate agents instead of doing everything yourself.
            2. Execute tools that match each step and return real data.
            3. If a step fails, retry with alternatives or request clarification.
            {discovery_context}
            {policy_context}
            """

        execution_task = Task(
            description=execution_task_description,
            agent=self.orchestrator.orchestrator,
            expected_output=f"""Produce a response grounded in actual tool outputs for: {user_prompt}

- List actions taken for each agent involved.
- Include concrete data obtained from tool calls.
- Highlight any policy or approval considerations encountered.""",
        )

        all_agents = [
            self.orchestrator.orchestrator
        ] + self.orchestrator.registry_agents
        agents_used = [agent.role for agent in all_agents]

        def combined_callback(step):
            if step_callback:
                try:
                    step_callback(step)
                except Exception as exc:
                    if getattr(self.orchestrator, "logger", None):
                        self.orchestrator.logger.warning(
                            "Crew planner callback error", error=str(exc)
                        )

        crew = Crew(
            name="multi-agent-disu-crewai",
            agents=all_agents,
            tasks=[execution_task],
            process=Process.hierarchical,
            verbose=True,
            memory=True,
            full_output=True,
            step_callback=combined_callback,
            planning=True,
            max_iter=25,
        )

        session = get_trace_session()
        session.discovery_called = True

        with ThreadPoolExecutor(max_workers=2) as executor:
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    executor,
                    crew.kickoff,
                )
            except Exception as exc:
                return ExecutionReport(
                    answer=f"CrewAI planner execution error: {str(exc)}",
                    plan=plan,
                    metadata={
                        "trace_id": trace_id,
                        "planner": self.name,
                        "error": str(exc),
                        "agents_used": agents_used,
                    },
                    errors=[str(exc)],
                )

        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        execution_trace = {
            "scenario": intent.scenario,
            "tools_executed": session.executed_tools,
            "tool_count": len(session.executed_tools),
            "discovery_called": session.discovery_called,
        }

        return ExecutionReport(
            answer=str(result),
            plan=plan,
            metadata={
                "trace_id": trace_id,
                "planner": self.name,
                "agents_used": agents_used,
                "execution_time_ms": execution_time,
                "execution_trace": execution_trace,
                "policy_version": (
                    intent.metadata.get("policy_version") if intent.metadata else None
                ),
            },
            errors=[],
        )
