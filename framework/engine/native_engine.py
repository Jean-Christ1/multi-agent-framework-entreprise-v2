"""
Native Engine for JAF framework.

Executes plans without external LLM dependencies - ideal for deterministic
actors and testing scenarios.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry
from framework.engine.engine_abstraction import EngineAbstraction
from framework.logging import get_logger, set_logging_context
from framework.types import Plan, PlanStep, PlanUpdate, StepResult
from framework.data.schema_registry import SchemaRegistry


class NativeEngine(EngineAbstraction):
    """
    Native execution engine for deterministic workflows.

    Unlike CrewAI adapter, this engine:
    - Does not use LLM for planning (uses config-driven or rule-based planning)
    - Executes tools directly without AI agent wrappers
    - Ideal for actors with llm_config=None

    For plan generation, you can either:
    1. Provide a pre-built plan via set_plan()
    2. Let the engine create a simple sequential plan from all actor tools
    """

    def __init__(
        self,
        default_plan: Optional[Plan] = None,
        *,
        wrap_outputs_with_envelope: bool = False,
    ):
        """
        Initialize native engine.

        Args:
            default_plan: Optional pre-built plan to use instead of generating one
            wrap_outputs_with_envelope: If True, wrap tool outputs in DataEnvelope for provenance
        """
        self._default_plan = default_plan
        self._plan_builder: Optional[Callable[[str, List[Actor]], Plan]] = None
        self._wrap_outputs_with_envelope = wrap_outputs_with_envelope
        self.logger = get_logger("native_engine")

    def set_plan(self, plan: Plan) -> None:
        """
        Set a pre-built plan to use for execution.

        Args:
            plan: Pre-defined execution plan
        """
        self._default_plan = plan

    def set_plan_builder(
        self,
        builder: Callable[[str, List[Actor]], Plan],
    ) -> None:
        """
        Set a custom plan builder function.

        Args:
            builder: Function that takes (goal, actors) and returns a Plan
        """
        self._plan_builder = builder

    async def generate_plan(
        self,
        goal: str,
        available_actors: List[Actor],
    ) -> Plan:
        """
        Generate an execution plan from a goal.

        Strategy:
        1. If a default plan is set, use it
        2. If a plan builder is set, use it
        3. Otherwise, create a sequential plan using all tools from first actor

        Args:
            goal: High-level objective
            available_actors: Available actors for the plan

        Returns:
            Execution plan
        """
        if not goal or not goal.strip():
            raise ValueError("Goal cannot be empty")

        if not available_actors:
            raise ValueError("No actors available for planning")

        # Strategy 1: Use pre-set plan
        if self._default_plan is not None:
            self.logger.info("Using pre-defined plan")
            return self._default_plan

        # Strategy 2: Use custom plan builder
        if self._plan_builder is not None:
            self.logger.info("Using custom plan builder")
            return self._plan_builder(goal, available_actors)

        # Strategy 3: Generate sequential plan from actor tools
        self.logger.info("Generating sequential plan from actor tools")
        return self._generate_sequential_plan(goal, available_actors)

    def _generate_sequential_plan(
        self,
        goal: str,
        actors: List[Actor],
    ) -> Plan:
        """
        Generate a simple sequential plan using all tools from all actors.

        This is a fallback strategy when no explicit plan is provided.
        Each tool becomes a step, executed in order.

        Args:
            goal: The goal (stored in context for tools to access)
            actors: Available actors

        Returns:
            Sequential plan with one step per tool
        """
        steps: List[PlanStep] = []

        for actor in actors:
            for tool in actor.tools:
                tool_name = tool.__name__

                # Try to infer parameters from tool signature
                sig = inspect.signature(tool)
                params: Dict[str, Any] = {}

                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue
                    # Use default if available, otherwise use placeholder
                    if param.default != inspect.Parameter.empty:
                        params[param_name] = param.default
                    else:
                        # Mark as needing value from context
                        params[param_name] = f"{{context.{param_name}}}"

                step = PlanStep(
                    actor_name=actor.name,
                    tool_name=tool_name,
                    parameters=params,
                    status="pending",
                )
                steps.append(step)

        return Plan(steps=steps, status="PLANNING")

    async def execute_step(
        self,
        step: PlanStep,
        context: Dict[str, Any],
    ) -> StepResult:
        """
        Execute a single plan step by directly invoking the tool.

        Args:
            step: Step to execute
            context: Execution context with intermediate results

        Returns:
            StepResult with output or error
        """
        start_time = datetime.now(timezone.utc)

        # Update context with actor and step info
        set_logging_context(actor_name=step.actor_name, step_id=step.id)

        try:
            # Get actor from registry
            actor = ActorRegistry.get(step.actor_name)

            # Find the tool
            tool = None
            for t in actor.tools:
                if t.__name__ == step.tool_name:
                    tool = t
                    break

            if tool is None:
                raise ValueError(
                    f"Tool '{step.tool_name}' not found on actor '{step.actor_name}'"
                )

            # Resolve parameters from context
            resolved_params = self._resolve_parameters(step.parameters, context)

            # --- Strict Tool Input Contract Validation ---
            contract = getattr(tool, "__tool_contract__", None)
            input_type = getattr(contract, "input", None)
            if input_type is not None:
                # Enforce: tool must have exactly one non-self parameter
                sig = inspect.signature(tool)
                params = [p for p in sig.parameters.values() if p.name != "self"]
                if len(params) != 1:
                    raise TypeError(
                        f"Tool '{step.actor_name}.{step.tool_name}' declares input={input_type.__name__} but has {len(params)} non-self parameters. "
                        "This is not supported. If you need multiple parameters, do not use input=... or handle validation explicitly."
                    )
                param_name = params[0].name
                from framework.data.validation import DataValidationError

                try:
                    resolved_params[param_name] = input_type.model_validate(
                        resolved_params[param_name]
                    )
                except Exception as ve:
                    # Always raise DataValidationError for input validation issues
                    self.logger.error(
                        f"Input validation failed for {step.actor_name}.{step.tool_name}: {ve}"
                    )
                    raise DataValidationError(
                        direction="input",
                        tool=f"{step.actor_name}.{step.tool_name}",
                        message=str(ve),
                        details=(
                            getattr(ve, "errors", lambda: None)()
                            if hasattr(ve, "errors")
                            else {}
                        ),
                    )
            # If no input contract, no validation is performed.

            # Execute the tool
            self.logger.info(f"Executing {step.actor_name}.{step.tool_name}")

            if asyncio.iscoroutinefunction(tool):
                result = await tool(**resolved_params)
            else:
                # Run sync function in executor to not block
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: tool(**resolved_params),
                )

            # --- Output Validation (Engine Orchestrated) ---
            validated_output = result
            # Always validate output if a contract is declared, even for dicts
            if contract and getattr(contract, "output", None):
                self.logger.debug(
                    f"Validating output for {step.actor_name}.{step.tool_name} with value: {result!r}"
                )
                try:
                    validated_output = contract.validate_output(result)
                except Exception as ve:
                    self.logger.error(
                        f"Output validation failed for {step.actor_name}.{step.tool_name}: {ve}"
                    )
                    from framework.data.validation import DataValidationError

                    self.logger.debug(f"Output validation raised: {ve}")
                    raise DataValidationError(
                        direction="output",
                        tool=f"{step.actor_name}.{step.tool_name}",
                        message=str(ve),
                        details=(
                            getattr(ve, "errors", lambda: None)()
                            if hasattr(ve, "errors")
                            else {}
                        ),
                    )

            # --- Output Pass-through (no normalization or provenance wrapping) ---
            output = validated_output
            # Always wrap primitive outputs in a dict for StepResult
            if not isinstance(output, dict):
                output = {"result": output}

            # Calculate execution time
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            self.logger.info(f"Step completed in {duration_ms}ms")

            return StepResult(
                output=output,
                status="success",
                execution_time=duration_ms,
            )

        except Exception as e:
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            self.logger.error(f"Step failed: {e}", exc_info=True)

            return StepResult(
                output={},
                status="error",
                error=str(e),
                execution_time=duration_ms,
            )

    # ---------------------------------------------------------------------
    # Output Lifecycle Documentation
    # ---------------------------------------------------------------------
    """
    Output Lifecycle (as of 2026-01-27):

    1. Tool executes and returns a result (may be a DataContract, dict, or primitive).
    2. If a ToolContract.output is declared, output is validated as a DataContract instance.
    3. Output is passed through as-is (no normalization or provenance wrapping).
    4. StepResult.output contains the raw output (DataContract, dict, or primitive).

    Provenance and serialization are not handled by the engine and should be managed elsewhere if needed.
    """

    def _resolve_parameters(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resolve parameter values from context.

        Handles placeholders like {context.key} by looking up values in context.

        Args:
            params: Parameter dict with potential placeholders
            context: Context to resolve values from

        Returns:
            Resolved parameters
        """
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{context."):
                # Extract context key
                context_key = value[9:-1]  # Remove "{context." and "}"
                if context_key in context:
                    resolved[key] = context[context_key]
                else:
                    # Keep placeholder if not found (let tool handle it)
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved

    async def evaluate_progress(
        self,
        plan: Plan,
        result: StepResult,
    ) -> PlanUpdate:
        """
        Evaluate progress after a step execution.

        Simple rule-based evaluation:
        - Error -> abort
        - Success with more steps -> continue
        - All steps done -> continue (signals completion)

        Args:
            plan: Current plan
            result: Result of last step

        Returns:
            PlanUpdate with decision
        """
        # Check for terminal plan states
        if plan.status == "COMPLETED":
            return PlanUpdate(
                action="continue",
                reason="Plan already completed",
            )

        if plan.status == "FAILED":
            return PlanUpdate(
                action="abort",
                reason="Plan is in failed state",
            )

        # Check step result
        if result.status == "error":
            return PlanUpdate(
                action="abort",
                reason=f"Step failed: {result.error or 'unknown error'}",
            )

        # Check for more pending steps
        next_step = plan.next_step()
        if next_step is None:
            return PlanUpdate(
                action="continue",
                reason="All steps completed",
            )

        return PlanUpdate(
            action="continue",
            reason="Step completed successfully, continuing to next step",
        )

    # ---------------------------------------------------------------------
    # Parallel Step Execution
    #
    # Description:
    # Add support for executing independent steps in parallel within NativeEngine.
    #
    # Acceptance Criteria:
    #
    #  Plan can mark steps as parallel_group: "group1"
    #
    #  Steps in same group execute concurrently
    #
    #  All parallel steps must complete before next group
    #
    #  Failure in one parallel step fails the group
    #
    #  Context merges results from all parallel steps
    # ---------------------------------------------------------------------

    def _get_parallel_group(self, step: PlanStep) -> Optional[str]:
        """
        Safe getter for PlanStep.parallel_group.

        Uses getattr to avoid runtime errors if older PlanStep instances exist without the field.
        """
        return getattr(step, "parallel_group", None)

    def _build_execution_batches(
        self, steps: List[PlanStep]
    ) -> List[tuple[Optional[str], List[PlanStep]]]:
        """
        Build execution batches from plan steps.

        Rules:
        - If parallel_group is None -> sequential batch of exactly 1 step
        - If parallel_group is set  -> consecutive steps with same group form one parallel batch
        """
        batches: List[tuple[Optional[str], List[PlanStep]]] = []
        i = 0

        while i < len(steps):
            pg = self._get_parallel_group(steps[i])

            if not pg:
                batches.append((None, [steps[i]]))
                i += 1
                continue

            group_steps: List[PlanStep] = []
            while i < len(steps) and self._get_parallel_group(steps[i]) == pg:
                group_steps.append(steps[i])
                i += 1

            batches.append((pg, group_steps))

        return batches

    def _merge_step_result_into_context(
        self, context: Dict[str, Any], result: StepResult
    ) -> None:
        """
        Merge StepResult into context.

        execute_step returns StepResult.output as dict, so we simply update().
        """
        if not result.output:
            return
        context.update(result.output)

    async def execute_plan(
        self, plan: Plan, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the full plan.

        Supports parallel execution when steps have parallel_group set.

        Technical notes
        # Plan with parallel steps
        steps = [
            PlanStep(..., parallel_group="fetch"),   # runs together
            PlanStep(..., parallel_group="fetch"),   # runs together
            PlanStep(..., parallel_group=None),      # runs after fetch group
        ]
        """
        if context is None:
            context = {}

        plan.status = "EXECUTING"

        batches = self._build_execution_batches(plan.steps)

        for pg, batch_steps in batches:
            # Sequential execution (single step)
            if pg is None:
                step = batch_steps[0]
                step.status = "executing"

                result = await self.execute_step(step, context)

                if result.status == "success":
                    step.status = "completed"
                    self._merge_step_result_into_context(context, result)
                else:
                    step.status = "failed"
                    plan.status = "FAILED"
                    raise RuntimeError(
                        f"Step failed: {step.actor_name}.{step.tool_name} - {result.error}"
                    )

                continue

            # Parallel execution (group)
            self.logger.info(
                f"Executing parallel group '{pg}' with {len(batch_steps)} step(s)"
            )

            for s in batch_steps:
                s.status = "executing"

            results: List[StepResult] = await asyncio.gather(
                *[self.execute_step(s, context) for s in batch_steps]
            )

            # Merge deterministically in plan order and detect failure
            any_error = False
            first_error_msg: Optional[str] = None

            for step, result in zip(batch_steps, results):
                if result.status == "success":
                    step.status = "completed"
                    self._merge_step_result_into_context(context, result)
                else:
                    step.status = "failed"
                    any_error = True
                    if first_error_msg is None:
                        first_error_msg = (
                            f"{step.actor_name}.{step.tool_name} - {result.error}"
                        )

            if any_error:
                plan.status = "FAILED"
                raise RuntimeError(
                    f"Parallel group '{pg}' failed. First error: {first_error_msg}"
                )

        plan.status = "COMPLETED"
        return context

    def get_tool_schema(self, actor_name: str, tool_name: str) -> dict:
        """
        Return the input/output schema for a given actor tool using SchemaRegistry.
        Useful for documentation, validation, or UI integration.
        """
        for schema in SchemaRegistry.collect_tool_schemas():
            if schema["actor"] == actor_name and schema["tool"] == tool_name:
                return schema
        return {}
