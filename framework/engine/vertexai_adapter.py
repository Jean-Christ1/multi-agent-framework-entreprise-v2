from __future__ import annotations

import json
from typing import Any, Dict, List


from framework.engine.engine_abstraction import EngineAbstraction
from framework.types import Plan, PlanStep, StepResult, PlanUpdate
from framework.exceptions import EngineException
from framework.deprecation import deprecated
from framework.logging import get_logger

logger = get_logger(__name__)


class VertexAIAdapter(EngineAbstraction):
    """
    Google VertexAI Adapter

    Implemented:
    - generate_plan()      (JAF-42)
    - execute_step()       (JAF-43)
    - evaluate_progress()  (JAF-44)
    """

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    # ------------------------------------------------------------------
    # JAF-42 — PLAN GENERATION
    # ------------------------------------------------------------------
    async def generate_plan(self, goal: str, actors: list[Any]) -> Plan:
        if not goal.strip():
            raise EngineException("Empty goal. Cannot generate a plan.")

        if not actors:
            raise EngineException("No available actors provided for planning.")

        actors_description = self._describe_actors(actors)
        prompt = self._build_prompt(goal, actors_description)

        raw_response = self.llm.generate(prompt)
        plan_dict = self._parse_json(raw_response)
        self._validate_plan(plan_dict, actors)

        steps = []
        for step in plan_dict["steps"]:
            steps.append(
                PlanStep(
                    id=step["step_id"],
                    actor_name=step["actor_name"],
                    tool_name=step["tool_name"],
                    parameters=step.get("parameters", {}),
                    status="pending",
                )
            )

        return Plan(
            steps=steps,
            status="PLANNING",
        )

    # ------------------------------------------------------------------
    # JAF-43 — EXECUTE STEP
    # ------------------------------------------------------------------
    @deprecated(
        reason="Raw dict outputs are being phased out",
        removal_version="0.3.0",
        replacement="Return a DataContract from tools and StepResult",
    )
    def execute_step(self, step: PlanStep, context: Dict[str, Any]) -> StepResult:
        actor = context.get("actors_by_name", {}).get(step.actor_name)
        if actor is None:
            raise EngineException(f"Actor not found: {step.actor_name}")

        tool = self._find_tool(actor, step.tool_name)
        if tool is None:
            raise EngineException(
                f"Tool '{step.tool_name}' not found on actor '{step.actor_name}'"
            )

        try:
            logger.info(
                "Executing step %s: %s.%s(%s)",
                step.id,
                step.actor_name,
                step.tool_name,
                step.parameters,
            )

            output = tool(**step.parameters)

            return StepResult(
                status="success",
                output=output,
                error=None,
            )

        except Exception as exc:
            logger.exception(
                "Execution failed for step %s (%s.%s)",
                step.id,
                step.actor_name,
                step.tool_name,
            )

            return StepResult(
                status="error",
                output={},
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # JAF-44 — EVALUATE PROGRESS
    # ------------------------------------------------------------------
    async def evaluate_progress(
        self,
        plan: Plan,
        result: StepResult,
    ) -> PlanUpdate:
        if result.status == "error":
            plan.status = "FAILED"

            return PlanUpdate(
                action="abort",
                reason=result.error or "Step execution failed.",
                modified_plan=plan,
            )

        remaining_steps = [step for step in plan.steps if step.status == "pending"]

        if remaining_steps:
            plan.status = "EXECUTING"

            return PlanUpdate(
                action="continue",
                reason="Proceed to next step.",
                modified_plan=plan,
            )

        plan.status = "COMPLETED"

        return PlanUpdate(
            action="continue",
            reason="All steps executed successfully.",
            modified_plan=plan,
        )

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------
    def _find_tool(self, actor: Any, tool_name: str):
        for tool in actor.tools:
            if tool.name == tool_name:
                return tool
        return None

    def _describe_actors(self, actors: list[Any]) -> str:
        lines: List[str] = []

        for actor in actors:
            lines.append(f"Actor: {actor.name}")

            description = getattr(actor, "description", "")
            if description:
                lines.append(f"  Description: {description}")

            tools = getattr(actor, "tools", [])
            if tools:
                lines.append("  Tools:")
                for tool in tools:
                    tool_desc = getattr(tool, "description", "") or ""
                    lines.append(f"    - {tool.name}: {tool_desc}")

            lines.append("")

        return "\n".join(lines)

    def _build_prompt(self, goal: str, actors_description: str) -> str:
        return f"""
You are a planning engine inside an AI orchestration framework.

STRICT RULES:
- Output ONLY valid JSON
- No markdown
- No comments
- No extra text
- Use ONLY the actors and tools listed
- step_id must be S1, S2, S3...

USER GOAL:
{goal}

AVAILABLE ACTORS AND TOOLS:
{actors_description}

EXPECTED JSON FORMAT:
{{
  "steps": [
    {{
      "step_id": "S1",
      "actor_name": "ActorName",
      "tool_name": "tool_name",
      "parameters": {{}}
    }}
  ]
}}

Return the JSON now.
""".strip()

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception as exc:
            logger.error("Invalid Vertex AI response: %s", text)
            raise EngineException("Failed to parse JSON returned by Vertex AI") from exc

    def _validate_plan(self, plan: Dict[str, Any], actors: list[Any]) -> None:
        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise EngineException("Invalid plan: missing 'steps' list.")

        actor_names = {actor.name for actor in actors}
        tools_by_actor = {
            actor.name: {tool.name for tool in actor.tools} for actor in actors
        }

        for step in plan["steps"]:
            actor_name = step.get("actor_name")
            tool_name = step.get("tool_name")

            if actor_name not in actor_names:
                raise EngineException(f"Unknown actor in plan: {actor_name}")

            if tool_name not in tools_by_actor[actor_name]:
                raise EngineException(
                    f"Unknown tool '{tool_name}' for actor '{actor_name}'"
                )
