from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from framework.engine.engine_abstraction import EngineAbstraction
from framework.types import (
    Plan,
    PlanStep,
    StepResult,
    PlanUpdate,
    LLMConfig,
    AgentAction,
)
from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry
from framework.event_bus import get_event_bus
from framework.logging import get_logger, set_logging_context
import json
import re


class CrewAIAdapter(EngineAbstraction):
    """
    Adapter that wraps CrewAI execution behind the EngineAbstraction interface.

    This adapter provides backward compatibility with existing CrewAI orchestrator
    while enabling integration with the new Actor-based framework (e.g., ProvisioningActor).

    This scaffold (JAF-5) establishes the contract and ensures compilation.
    """

    def _get_llm(self, config: Optional[LLMConfig]):
        """
        Configure the LLM model for CrewAI
        If there is no config, CrewAI will use the default (GPT-4).
        """
        if not config:
            return None

        try:
            from langchain_openai import ChatOpenAI

            # You can expand here for Anthropic, Azure, etc.
            return ChatOpenAI(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout=30,
            )
        except ImportError:
            # If langchain_openai is not installed, we let CrewAI manage it through environment variables.
            return None

    def __init__(self, llm_client=None):
        """
        Initialize CrewAI adapter.

        Args:
            llm_client: Optional LLM client for plan generation (e.g., OpenAI, Anthropic)
                       If None, will need to be set before calling generate_plan
        """
        self.logger = get_logger("crewai_adapter")
        self.llm_client = llm_client
        self._event_bus = get_event_bus()

    async def generate_plan(self, goal: str, available_actors: List[Actor]) -> Plan:
        """
        Generate an execution plan from a high-level goal using LLM-based planning.

        This method:
        1. Gathers metadata about available actors and their tools
        2. Constructs a prompt for the LLM describing the goal and capabilities
        3. Asks the LLM to generate a step-by-step plan
        4. Parses the LLM response into a structured Plan object

        Args:
            goal: High-level objective to achieve (e.g., "Provision a new AWS EC2 instance")
            available_actors: List of actors that can execute plan steps

        Returns:
            Plan: Structured execution plan with ordered PlanSteps

        Raises:
            ValueError: If no actors available or goal is empty
            RuntimeError: If LLM call fails or response is invalid
        """
        if not goal or not goal.strip():
            raise ValueError("Goal cannot be empty")

        if not available_actors:
            raise ValueError("No actors available for planning")

        if self.llm_client is None:
            self.logger.warning("LLM client not configured, using fallback planner")
            return self._fallback_plan(goal, available_actors)

        # Step 1: Build actor capabilities description
        actor_capabilities = self._build_actor_capabilities(available_actors)

        # Step 2: Construct planning prompt
        planning_prompt = self._build_planning_prompt(goal, actor_capabilities)

        # Step 3: Call LLM to generate plan
        try:
            llm_response = await self._call_llm(planning_prompt)
            self.logger.info(f"LLM response received for goal: {goal}")
        except Exception as e:
            self.logger.error(
                f"LLM call failed, falling back to deterministic plan: {e}"
            )
            return self._fallback_plan(goal, available_actors)

        # Step 4: Parse LLM response into Plan
        try:
            plan = self._parse_plan_from_response(llm_response, available_actors)
            self.logger.info(f"Generated plan with {len(plan.steps)} steps")
            return plan
        except Exception as e:
            self.logger.error(f"Failed to parse LLM plan, falling back: {e}")
            return self._fallback_plan(goal, available_actors)

    def _fallback_plan(self, goal: str, actors: List[Actor]) -> Plan:
        """
        Deterministic fallback planner.
        Produces a minimal valid plan for demo / tests.
        """
        actor = actors[0]

        if not actor.tools:
            raise RuntimeError(f"Actor '{actor.name}' has no tools for fallback plan")

        step = PlanStep(
            actor_name=actor.name,
            tool_name=actor.tools[0].__name__,
            parameters={"goal": goal},
            status="pending",
        )

        return Plan(steps=[step], status="PLANNING")

    def _build_actor_capabilities(self, actors: List[Actor]) -> str:
        """
        Build a formatted string describing available actors and their tools.

        Args:
            actors: List of Actor instances

        Returns:
            Formatted string with actor capabilities
        """
        capabilities = []

        for actor in actors:
            actor_info = [
                f"Actor: {actor.name}",
                f"Description: {actor.description}",
                f"Goal: {actor.goal}",
                "Available Tools:",
            ]

            for tool in actor.tools:
                tool_name = tool.__name__
                tool_doc = (tool.__doc__ or "No description").strip()

                # Extract parameter information from function signature
                import inspect

                sig = inspect.signature(tool)
                params = []
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue
                    param_type = (
                        param.annotation
                        if param.annotation != inspect._empty
                        else "Any"
                    )
                    params.append(f"{param_name}: {param_type}")

                params_str = ", ".join(params) if params else "no parameters"
                actor_info.append(f"  - {tool_name}({params_str}): {tool_doc}")

            capabilities.append("\n".join(actor_info))

        return "\n\n".join(capabilities)

    def _build_planning_prompt(self, goal: str, capabilities: str) -> str:
        """
        Construct the LLM prompt for plan generation.

        Args:
            goal: User's high-level goal
            capabilities: Formatted string of actor capabilities

        Returns:
            Complete prompt for the LLM
        """
        prompt = f"""You are a task planning assistant. Your job is to break down a high-level goal into a sequence of executable steps.

        GOAL:
        {goal}

        AVAILABLE ACTORS AND TOOLS:
        {capabilities}

        INSTRUCTIONS:
        1. Analyze the goal and identify the key steps needed to achieve it
        2. For each step, select the most appropriate actor and tool from those available
        3. Define the parameters needed for each tool call
        4. Order the steps logically (dependencies should be respected)
        5. Return ONLY a JSON array of steps in this exact format:

        [
        {{
            "actor_name": "ActorName",
            "tool_name": "tool_function_name",
            "parameters": {{"param1": "value1", "param2": "value2"}},
            "description": "Brief description of what this step does"
        }}
        ]

        IMPORTANT:
        - Only use actors and tools from the list above
        - Ensure parameters match the tool signatures
        - Keep the plan minimal but complete
        - Return ONLY the JSON array, no additional text
        """
        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM to generate a plan.

        This is a placeholder that should be replaced with actual LLM API calls
        (OpenAI, Anthropic, etc.) based on your LLM client configuration.

        Args:
            prompt: The planning prompt

        Returns:
            LLM response as string
        """
        # Example implementation for OpenAI-style client:
        if hasattr(self.llm_client, "chat"):
            # OpenAI style
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.choices[0].message.content

        elif hasattr(self.llm_client, "messages"):
            # Anthropic style
            response = await self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.content[0].text

        else:
            # Generic callable
            return await self.llm_client(prompt)

    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON content from an LLM response.
        Handles raw JSON or JSON wrapped in markdown code blocks.
        """
        response = response.strip()

        # Match markdown code block ```json ... ``` or ``` ... ```
        match = re.search(
            r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        # Fallback: assume entire response is JSON
        return response

    def _parse_plan_from_response(self, response: str, actors: List[Actor]) -> Plan:
        """
        Parse LLM response into a Plan object.

        Args:
            response: LLM response containing JSON plan
            actors: Available actors for validation

        Returns:
            Plan object with parsed steps

        Raises:
            ValueError: If response format is invalid
        """
        # Extract JSON from response (handle markdown code blocks)
        response = self._extract_json_from_response(response)

        # Parse JSON
        try:
            steps_data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        if not isinstance(steps_data, list):
            raise ValueError("Expected JSON array of steps")

        # Build actor lookup
        actor_map = {actor.name: actor for actor in actors}

        # Convert to PlanStep objects
        plan_steps = []
        for i, step_data in enumerate(steps_data):
            try:
                actor_name = step_data["actor_name"]
                tool_name = step_data["tool_name"]
                parameters = step_data.get("parameters", {})

                # Validate actor exists
                if actor_name not in actor_map:
                    raise ValueError(f"Unknown actor: {actor_name}")

                # Validate tool exists on actor
                actor = actor_map[actor_name]
                tool_names = [t.__name__ for t in actor.tools]
                if tool_name not in tool_names:
                    raise ValueError(f"Actor {actor_name} has no tool {tool_name}")

                # Create PlanStep
                plan_step = PlanStep(
                    actor_name=actor_name,
                    tool_name=tool_name,
                    parameters=parameters,
                    status="pending",
                )
                plan_steps.append(plan_step)

            except KeyError as e:
                raise ValueError(f"Step {i} missing required field: {e}")

        # Create and return Plan
        plan = Plan(steps=plan_steps, status="PLANNING")
        return plan

    async def execute_step(self, step: PlanStep, context: Dict[str, Any]) -> StepResult:
        """
        Execute a single PlanStep using CrewAI.

        Emits events:
        - started: When execution begins (actionType="started")
        - tool_name: On successful completion (actionType=step.tool_name)
        - tool_name: On failure (actionType=step.tool_name, status="error")

        Args:
            step: PlanStep to execute
            context: Execution context

        Returns:
            StepResult with output or error
        """
        # Set logging context for this step execution
        set_logging_context(
            actor_name=step.actor_name,
            step_id=step.id,
        )

        try:
            from crewai import Agent, Task, Crew, Process
            from crewai.tools import tool as crew_tool
        except ImportError as e:
            error_msg = f"CrewAI dependencies missing: {str(e)}"
            self.logger.error(error_msg)
            # Emit error event for missing dependencies
            self._event_bus.emit(
                AgentAction(
                    agentId=step.actor_name,
                    actionType=step.tool_name,
                    message=f"Step failed: {error_msg}",
                    status="error",
                )
            )
            return StepResult(
                output={},
                status="error",
                error=error_msg,
            )

        start_time = datetime.now(timezone.utc)

        # Log step execution start
        self.logger.info(f"Executing {step.actor_name}.{step.tool_name} via CrewAI")

        # Emit step started event
        self._event_bus.emit(
            AgentAction(
                agentId=step.actor_name,
                actionType="started",
                message=f"Starting execution of {step.tool_name}",
                status="complete",
            )
        )

        try:
            # 1. Get Actor from registry
            actor = ActorRegistry.get(step.actor_name)

            # 2. Filter tools to only the requested one
            selected_tools = []
            for t in actor.tools:
                t_name = getattr(t, "__name__", getattr(t, "name", None))

                if t_name == step.tool_name:
                    if not hasattr(t, "args_schema"):
                        wrapped = crew_tool(t_name)(t)
                        selected_tools.append(wrapped)
                    else:
                        selected_tools.append(t)

            if not selected_tools:
                raise ValueError(
                    f"Tool '{step.tool_name}' not found for actor '{actor.name}'"
                )

            # 3. Create CrewAI Agent
            crew_agent = Agent(
                role=actor.name,
                goal=actor.goal or step.tool_name,
                backstory=actor.description,
                tools=selected_tools,
                llm=self._get_llm(actor.llm_config),
                verbose=True,
                allow_delegation=False,
            )

            # 4. Create Task
            task = Task(
                description=(
                    f"Action: Execute tool '{step.tool_name}' with parameters {step.parameters}. "
                    f"Current context: {context}"
                ),
                expected_output="The final output of the tool execution.",
                agent=crew_agent,
            )

            # 5. Run Crew (single agent, single task)
            crew = Crew(
                agents=[crew_agent],
                tasks=[task],
                process=Process.sequential,
            )

            result = crew.kickoff()

            # 6. Calculate execution time
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            # Log successful completion
            self.logger.info(
                f"Completed {step.actor_name}.{step.tool_name} in {duration_ms}ms"
            )

            # 7. Emit step completed event
            self._event_bus.emit(
                AgentAction(
                    agentId=step.actor_name,
                    actionType=step.tool_name,
                    message=f"Completed {step.tool_name} in {duration_ms}ms",
                    status="complete",
                )
            )

            # 8. Map to StepResult
            return StepResult(
                output={"result": result},
                status="success",
                execution_time=duration_ms,
            )

        except Exception as e:
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            error_message = str(e)

            # Log step failure with exception details
            self.logger.error(
                f"Step {step.actor_name}.{step.tool_name} failed: {error_message}",
                exc_info=True,
            )

            # Emit step error event
            self._event_bus.emit(
                AgentAction(
                    agentId=step.actor_name,
                    actionType=step.tool_name,
                    message=f"Step {step.tool_name} failed: {error_message}",
                    status="error",
                )
            )

            return StepResult(
                output={},
                status="error",
                error=error_message,
                execution_time=duration_ms,
            )

    async def evaluate_progress(self, plan: Plan, result: StepResult) -> PlanUpdate:
        """
        Evaluate plan progress after a step execution.

        Logic:
        - COMPLETED status -> continue
        - FAILED status    -> abort
        - Step error       -> abort
        - Empty output     -> modify (trigger re-planning)
        - Otherwise        -> continue
        """

        # 1. Guard: Plan already in terminal state
        if plan.status == "COMPLETED":
            return PlanUpdate(
                action="continue", reason="Plan already completed successfully."
            )

        if plan.status == "FAILED":
            return PlanUpdate(action="abort", reason="Plan is already in FAILED state.")

        # 2. Step execution failed: Abort
        if result.status == "error":
            return PlanUpdate(
                action="abort",
                reason=f"Step execution failed: {result.error or 'unknown error'}",
            )

        # 3. Step succeeded but returned no meaningful output
        if result.status == "success" and not result.output:
            return PlanUpdate(
                action="modify",
                reason="Step succeeded but produced no output; plan may need adjustment",
            )

        # 4. Check if there are more steps to execute
        next_step = plan.next_step()
        if next_step is None:
            return PlanUpdate(action="continue", reason="All steps completed")

        # 5. Default: Everything is good, continue execution
        return PlanUpdate(
            action="continue", reason="Step completed successfully, moving to next step"
        )
