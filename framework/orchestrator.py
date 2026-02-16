"""Orchestrator - Main execution coordinator for JAF framework.

Coordinates the Engine, Actors, EventBus, and Persistence to execute
agentic workflows from start to finish.

Supports dry-run mode: validates plans and simulates execution without side effects or tool calls.
"""

from __future__ import annotations

import asyncio
import inspect
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Type
from uuid import UUID

from framework.actor.base_actor import Actor
from framework.actor.registry import ActorRegistry
from framework.data.context import TypedContext
from framework.engine.engine_abstraction import EngineAbstraction
from framework.event_bus import EventBus, get_event_bus
from framework.logging import get_logger, set_logging_context
from framework.persistence.models import ProcessStatus
from framework.persistence.process_repo import ProcessRepository
from framework.state_machine import ProcessStateMachine
from framework.tools.contracts import ToolContract
from framework.types import AgentAction, Plan, StepResult


# --- Validation Models for Dry-Run ---
@dataclass
class ValidationIssue:
    step_index: int
    level: Literal["error", "warning"]
    message: str


@dataclass
class ValidationReport:
    valid: bool
    issues: List[ValidationIssue]


class StepTimeoutError(TimeoutError):
    """Raised when a plan step execution exceeds the configured timeout."""

    def __init__(
        self,
        *,
        timeout_seconds: int,
        step_index: int,
        total_steps: int,
        actor_name: str,
        tool_name: str,
        process_id: uuid.UUID,
    ):
        self.timeout_seconds = timeout_seconds
        self.step_index = step_index
        self.total_steps = total_steps
        self.actor_name = actor_name
        self.tool_name = tool_name
        self.process_id = process_id

        super().__init__(
            f"Step timed out after {timeout_seconds}s "
            f"(step {step_index}/{total_steps}: {actor_name}.{tool_name}, process={process_id})"
        )


@dataclass
class ProcessResult:
    """Result of orchestrator execution."""

    process_id: Optional[uuid.UUID]
    status: ProcessStatus
    plan: Plan
    context: Dict[str, Any]
    error: Optional[str] = None
    step_results: List[StepResult] = field(default_factory=list)
    validation_report: Optional[ValidationReport] = None
    dry_run: bool = False


class Orchestrator:
    """
    Main execution coordinator for JAF framework.

    Orchestrates the full process lifecycle:
    1. Create process (PENDING)
    2. Generate plan using Engine (RUNNING)
    3. Execute steps sequentially
    4. Evaluate progress after each step
    5. Update process state
    6. Emit events throughout

    Usage:
        orchestrator = Orchestrator(engine, session_maker, step_timeout=60)
        result = await orchestrator.run(goal="...", actors=[...])

    Retry policy usage (ticket):
        orchestrator = Orchestrator(
            engine=engine,
            session_maker=session_maker,
            max_retries=3,
            retry_delay=5,
            retry_on=[ConnectionError, TimeoutError],
        )
    """

    def __init__(
        self,
        engine: EngineAbstraction,
        session_maker,
        event_bus: Optional[EventBus] = None,
        step_timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        retry_on: Optional[Sequence[Type[BaseException]]] = None,
    ):
        """
        Initialize orchestrator.

        Args:
            engine: Engine implementation (CrewAI, Native, etc.)
            session_maker: Async session factory for database
            event_bus: Optional EventBus instance (defaults to singleton)
            step_timeout: Default timeout per step in seconds (configurable)
            max_retries: How many retries for transient failures (default 3)
            retry_delay: Base delay in seconds, doubles each retry (exponential backoff)
            retry_on: List of exception types that should trigger retries
                      Defaults to (ConnectionError, TimeoutError)
        """
        self.engine = engine
        self.session_maker = session_maker
        self.event_bus = event_bus or get_event_bus()
        self.step_timeout = step_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_on: Tuple[Type[BaseException], ...] = tuple(
            retry_on if retry_on is not None else (ConnectionError, TimeoutError)
        )
        self.logger = get_logger("orchestrator")

    async def run(
        self,
        goal: str,
        actors: List[Actor],
        context: Optional[Dict[str, Any]] = None,
        process_id: Optional[uuid.UUID] = None,
        dry_run: bool = False,
    ) -> ProcessResult:
        """
        Execute the full orchestration loop.

        Args:
            goal: High-level objective to achieve
            actors: List of actors available for the plan
            context: Optional initial context
            process_id: Optional process ID (auto-generated if not provided)

        Returns:
            ProcessResult with final status, plan, and context
        """
        if dry_run:
            # Hard early exit: no side effects, no DB, no events, no UUID
            context = context or {}
            plan = await self.engine.generate_plan(goal, actors)
            validation_report = self._validate_plan(plan, actors)
            return ProcessResult(
                process_id=None,
                status=ProcessStatus.DRY_RUN,
                plan=plan,
                context=context,
                validation_report=validation_report,
                dry_run=True,
            )

        process_id = process_id or uuid.uuid4()
        set_logging_context(process_id=str(process_id))
        context = context or {}
        typed_ctx = TypedContext(initial=context)
        step_results: List[StepResult] = []
        current_status = ProcessStateMachine.get_initial_status()

        self.logger.info("Starting orchestration")
        self._emit_event("process_started", f"Starting process with goal: {goal}")

        try:
            async with self.session_maker() as session:
                repo = ProcessRepository(session)

                # 1. Create process in DB (PENDING)
                initial_plan = Plan(steps=[], status="PLANNING")
                await repo.create_process(
                    process_id=process_id,
                    plan=initial_plan,
                    context=typed_ctx.to_dict(),
                    status=current_status,
                )
                self.logger.info(f"Process created with status {current_status.value}")

                initial_plan = Plan(steps=[], status="PLANNING")

                # Phase 2: Transition to RUNNING and generate plan
                current_status = await self._transition_status(
                    repo,
                    process_id,
                    initial_plan,
                    typed_ctx,
                    current_status,
                    ProcessStatus.RUNNING,
                )

                # 2. Generate plan (RUNNING)
                plan = await self.engine.generate_plan(goal, actors)
                await repo.update_process(
                    process_id=process_id,
                    plan=plan,
                    context=typed_ctx.to_dict(),
                    status=ProcessStatus.RUNNING,
                )
                current_status = ProcessStatus.RUNNING

                # 3. Execute steps
                result = await self._execute_steps(
                    repo=repo,
                    process_id=process_id,
                    plan=plan,
                    context=typed_ctx,
                    current_status=current_status,
                    step_results=step_results,
                    start_index=0,
                )
                return result

        except Exception as e:
            self.logger.error(f"Process failed with error: {e}", exc_info=True)
            self._emit_event(
                "process_failed", f"Process failed: {str(e)}", status="error"
            )

            # Try to update process status to FAILED
            try:
                async with self.session_maker() as session:
                    repo = ProcessRepository(session)
                    failed_plan = Plan(steps=[], status="FAILED")
                    await repo.update_process(
                        process_id=process_id,
                        plan=failed_plan,
                        context=typed_ctx.to_dict(),
                        status=ProcessStatus.FAILED,
                    )
            except Exception as update_error:
                self.logger.error(f"Failed to update process status: {update_error}")

            return ProcessResult(
                process_id=process_id,
                status=ProcessStatus.FAILED,
                plan=Plan(steps=[], status="FAILED"),
                context=typed_ctx.to_dict(),
                error=str(e),
                step_results=step_results,
            )

    # ------------------------------------------------------------------
    # DRY RUN VALIDATION
    # ------------------------------------------------------------------
    def _validate_plan(self, plan: Plan, actors: List[Actor]) -> ValidationReport:
        issues: List[ValidationIssue] = []

        for i, step in enumerate(plan.steps):
            actor_name = step.actor_name
            tool_name = step.tool_name

            # 1. Actor exists
            try:
                actor = ActorRegistry.get(actor_name)
            except Exception:
                issues.append(
                    ValidationIssue(
                        step_index=i,
                        level="error",
                        message=f"Actor '{actor_name}' not found in registry",
                    )
                )
                continue

            # 2. Tool exists
            if not hasattr(actor, tool_name):
                issues.append(
                    ValidationIssue(
                        step_index=i,
                        level="error",
                        message=f"Tool '{tool_name}' not found on actor '{actor_name}'",
                    )
                )
                continue

            tool = getattr(actor, tool_name)

            # 3. Signature validation (exactly one parameter)
            try:
                sig = inspect.signature(tool)
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        step_index=i,
                        level="error",
                        message=f"Cannot inspect signature for {actor_name}.{tool_name}: {e}",
                    )
                )
                continue

            params = list(sig.parameters.values())

            if len(params) != 1:
                issues.append(
                    ValidationIssue(
                        step_index=i,
                        level="error",
                        message=(
                            f"{actor_name}.{tool_name} must take exactly one parameter "
                            f"(got {len(params)})"
                        ),
                    )
                )
                continue

            param_name = params[0].name

            # 4. DataContract validation
            contract: Optional[ToolContract] = getattr(tool, "__tool_contract__", None)

            if contract and contract.input:
                if param_name not in step.parameters:
                    issues.append(
                        ValidationIssue(
                            step_index=i,
                            level="error",
                            message=(
                                f"Missing parameter '{param_name}' for "
                                f"{actor_name}.{tool_name}"
                            ),
                        )
                    )
                    continue

                value = step.parameters.get(param_name)

                try:
                    contract.input.model_validate(value)
                except Exception as e:
                    issues.append(
                        ValidationIssue(
                            step_index=i,
                            level="error",
                            message=f"Invalid input for {actor_name}.{tool_name}: {e}",
                        )
                    )

        return ValidationReport(
            valid=not any(issue.level == "error" for issue in issues),
            issues=issues,
        )

    async def resume(self, process_id: UUID) -> ProcessResult:
        """Resume a process from its last saved state."""
        step_results: List[StepResult] = []
        context: Dict[str, Any] = {}
        set_logging_context(process_id=str(process_id))

        self.logger.info("Resuming orchestration")
        # emit resume event
        self._emit_event("process_resumed", "Resuming process")

        try:
            async with self.session_maker() as session:
                repo = ProcessRepository(session)

                # Load from DB
                try:
                    persisted = await repo.get_process(process_id)

                except ValueError as e:
                    self.logger.warning(f"Process not found: {e}")
                    return ProcessResult(
                        process_id=process_id,
                        status=ProcessStatus.FAILED,
                        plan=Plan(steps=[], status="FAILED"),
                        context={},
                        error=f"Process not found: {e}",
                    )

                except Exception:
                    self.logger.error(
                        "Unexpected error while resuming process",
                        exc_info=True,
                    )
                    raise

                plan = persisted.current_plan
                context = persisted.context or {}
                typed_ctx = TypedContext(initial=context)
                current_status = persisted.status

                # If process is already terminal, do nothing
                if current_status in (ProcessStatus.COMPLETED, ProcessStatus.FAILED):
                    return ProcessResult(
                        process_id=process_id,
                        status=current_status,
                        plan=plan,
                        context=typed_ctx.to_dict(),
                        error=(
                            None
                            if current_status == ProcessStatus.COMPLETED
                            else "Process already failed"
                        ),
                        step_results=step_results,
                    )

                # Ensure RUNNING (in case it was left pending)
                if current_status == ProcessStatus.PENDING:
                    current_status = await self._transition_status(
                        repo,
                        process_id,
                        plan,
                        typed_ctx,
                        current_status,
                        ProcessStatus.RUNNING,
                    )

                # Find first step that is not completed.
                # If crash happened while a step was "executing", reset it to "pending".
                start_index: Optional[int] = None
                for i, step in enumerate(plan.steps):
                    if step.status != "completed":
                        start_index = i
                        if step.status == "executing":
                            step.status = "pending"
                        break

                # If all steps are completed but process status wasn't updated, finalize it
                if start_index is None:
                    if not plan.steps:
                        self.logger.warning(
                            "Process resumed with an EMPTY plan. Finalizing as completed."
                        )
                    else:
                        self.logger.info(
                            "Process resumed with ALL steps already completed. Finalizing."
                        )

                    plan.status = "COMPLETED"
                    current_status = await self._transition_status(
                        repo,
                        process_id,
                        plan,
                        typed_ctx,
                        current_status,
                        ProcessStatus.COMPLETED,
                    )
                    self._emit_event(
                        "process_completed", "Process completed successfully"
                    )

                    return ProcessResult(
                        process_id=process_id,
                        status=current_status,
                        plan=plan,
                        context=typed_ctx.to_dict(),
                        step_results=step_results,
                    )

                # Persist potential reset + mark plan executing
                plan.status = "EXECUTING"
                await repo.update_process(
                    process_id=process_id,
                    plan=plan,
                    context=typed_ctx.to_dict(),
                    status=current_status,
                )

                # Continue executing steps from start_index
                result = await self._execute_steps(
                    repo=repo,
                    process_id=process_id,
                    plan=plan,
                    context=typed_ctx,
                    current_status=current_status,
                    step_results=step_results,
                    start_index=start_index,
                )

                return result

        except Exception as e:
            self.logger.error(f"Process resume failed with error: {e}", exc_info=True)
            self._emit_event(
                "process_failed", f"Resume failed: {str(e)}", status="error"
            )

            # Try to update process status to FAILED (best-effort) without losing plan/context
            try:
                async with self.session_maker() as session:
                    repo = ProcessRepository(session)
                    persisted = await repo.get_process(process_id)
                    failed_plan = persisted.current_plan
                    failed_context = persisted.context or context or {}

                    failed_plan.status = "FAILED"

                    await repo.update_process(
                        process_id=process_id,
                        plan=failed_plan,
                        context=failed_context,
                        status=ProcessStatus.FAILED,
                    )
            except Exception as update_error:
                self.logger.error(f"Failed to update process status: {update_error}")

            return ProcessResult(
                process_id=process_id,
                status=ProcessStatus.FAILED,
                plan=Plan(steps=[], status="FAILED"),
                context=context or {},
                error=str(e),
                step_results=step_results,
            )

    async def _execute_steps(
        self,
        repo: ProcessRepository,
        process_id: uuid.UUID,
        plan: Plan,
        context: TypedContext,
        current_status: ProcessStatus,
        step_results: List[StepResult],
        start_index: int,
        dry_run: bool = False,
    ) -> ProcessResult:
        """
        Execute plan steps from start_index onwards.

        Args:
            repo: Process repository
            process_id: Process ID
            plan: Current plan
            context: Current context
            current_status: Current process status
            step_results: List to append step results to
            start_index: Index to start execution from

            dry_run: If True, should never execute steps (guard)

        Returns:
            ProcessResult with final status, plan, and context
        """
        if dry_run:
            raise RuntimeError(
                "Engine step execution must never be called in dry_run mode."
            )
        for i in range(start_index, len(plan.steps)):
            step = plan.steps[i]

            step_number = i + 1
            total_steps = len(plan.steps)

            set_logging_context(actor_name=step.actor_name, step_id=step.id)
            self.logger.info(
                f"Executing step {step_number}/{total_steps}: {step.tool_name}"
            )
            self._emit_event(
                "step_started",
                f"Executing step {step_number}: {step.actor_name}.{step.tool_name}",
            )

            # Mark step as executing
            step.status = "executing"
            await repo.update_process(
                process_id=process_id,
                plan=plan,
                context=context.to_dict(),
            )

            # RETRY POLICY
            attempts_total = 1 + self.max_retries
            attempt = 0

            while True:
                attempt += 1

                try:
                    result = await asyncio.wait_for(
                        self.engine.execute_step(step, context),
                        timeout=self.step_timeout,
                    )
                    break

                except asyncio.TimeoutError:
                    err = StepTimeoutError(
                        timeout_seconds=self.step_timeout,
                        step_index=step_number,
                        total_steps=total_steps,
                        actor_name=getattr(step, "actor_name", "unknown"),
                        tool_name=getattr(step, "tool_name", "unknown"),
                        process_id=process_id,
                    )

                except asyncio.CancelledError:
                    # Never swallow cancellations in async code
                    raise

                except Exception as e:
                    err = e  # type: ignore[assignment]

                retryable = isinstance(err, self.retry_on)

                # If not retryable OR no retries left -> go to your existing failure path
                if (not retryable) or (attempt >= attempts_total):
                    if isinstance(err, StepTimeoutError):
                        self.logger.error(
                            "Step timeout: process=%s step=%s/%s actor=%s tool=%s timeout=%ss",
                            process_id,
                            step_number,
                            total_steps,
                            getattr(step, "actor_name", "unknown"),
                            getattr(step, "tool_name", "unknown"),
                            self.step_timeout,
                            exc_info=True,
                        )

                        step.status = "failed"
                        context["last_error"] = str(err)
                        context["timeout"] = {
                            "process_id": str(process_id),
                            "step_number": step_number,
                            "total_steps": total_steps,
                            "actor_name": getattr(step, "actor_name", "unknown"),
                            "tool_name": getattr(step, "tool_name", "unknown"),
                            "timeout_seconds": self.step_timeout,
                        }

                        # Persist progress
                        await repo.update_process(
                            process_id=process_id, plan=plan, context=context.to_dict()
                        )

                        # Emit event
                        self._emit_event("step_timeout", str(err), status="error")

                        # Mark process failed with clear error message
                        plan.status = "FAILED"
                        # Clear step-specific context before transitioning
                        set_logging_context(actor_name=None, step_id=None)
                        current_status = await self._transition_status(
                            repo,
                            process_id,
                            plan,
                            context,
                            current_status,
                            ProcessStatus.FAILED,
                        )
                        self._emit_event("process_failed", str(err), status="error")

                        return ProcessResult(
                            process_id=process_id,
                            status=current_status,
                            plan=plan,
                            context=context.to_dict(),
                            error=str(err),
                            step_results=step_results,
                        )

                    # Non-timeout final failure (new for retry policy) -> mark FAILED with clear error
                    step.status = "failed"
                    context["last_error"] = str(err)

                    await repo.update_process(
                        process_id=process_id, plan=plan, context=context.to_dict()
                    )

                    self._emit_event(
                        "step_failed",
                        f"Step {step_number} failed: {str(err)}",
                        status="error",
                    )

                    plan.status = "FAILED"
                    # Clear step-specific context before transitioning
                    set_logging_context(actor_name=None, step_id=None)
                    current_status = await self._transition_status(
                        repo,
                        process_id,
                        plan,
                        context,
                        current_status,
                        ProcessStatus.FAILED,
                    )
                    self._emit_event("process_failed", str(err), status="error")

                    return ProcessResult(
                        process_id=process_id,
                        status=current_status,
                        plan=plan,
                        context=context.to_dict(),
                        error=str(err),
                        step_results=step_results,
                    )

                # We have retries left AND it is retryable:
                retry_number = attempt  # attempt=1 failed => retry_number=1
                delay = self.retry_delay * (2 ** (retry_number - 1))

                self.logger.warning(
                    "Retrying step due to transient error: process=%s step=%s/%s actor=%s tool=%s retry=%s/%s delay=%ss error=%s",
                    process_id,
                    step_number,
                    total_steps,
                    getattr(step, "actor_name", "unknown"),
                    getattr(step, "tool_name", "unknown"),
                    retry_number,
                    self.max_retries,
                    delay,
                    str(err),
                )

                # Emit step_retried event (required)
                self._emit_event(
                    "step_retried",
                    (
                        f"Retry {retry_number}/{self.max_retries} for step {step_number} "
                        f"({getattr(step, 'actor_name', 'unknown')}.{getattr(step, 'tool_name', 'unknown')}) "
                        f"after error: {str(err)}. Next attempt in {delay}s."
                    ),
                    status="error",
                )

                context["last_error"] = str(err)
                context["retry"] = {
                    "process_id": str(process_id),
                    "step_number": step_number,
                    "attempt": attempt,
                    "max_retries": self.max_retries,
                    "delay_seconds": delay,
                    "error": str(err),
                }
                await repo.update_process(
                    process_id=process_id, plan=plan, context=context.to_dict()
                )

                await asyncio.sleep(delay)

            step_results.append(result)

            # Update context with result
            context[f"step_{i}_result"] = result.output
            context["last_result"] = result.output

            if result.status == "success":
                step.status = "completed"
                self._emit_event(
                    "step_completed",
                    f"Step {step_number} completed successfully",
                )
            else:
                step.status = "failed"
                self._emit_event(
                    "step_failed",
                    f"Step {step_number} failed: {result.error}",
                    status="error",
                )

            # Save progress
            await repo.update_process(
                process_id=process_id,
                plan=plan,
                context=context.to_dict(),
            )

            # Evaluate progress
            update = await self.engine.evaluate_progress(plan, result)
            self.logger.info(f"Evaluation result: {update.action} - {update.reason}")

            if update.action == "abort":
                self.logger.warning(f"Aborting process: {update.reason}")
                plan.status = "FAILED"
                # Clear step-specific context before transitioning
                set_logging_context(actor_name=None, step_id=None)
                current_status = await self._transition_status(
                    repo,
                    process_id,
                    plan,
                    context,
                    current_status,
                    ProcessStatus.FAILED,
                )
                return ProcessResult(
                    process_id=process_id,
                    status=current_status,
                    plan=plan,
                    context=context.to_dict(),
                    error=update.reason,
                    step_results=step_results,
                )

            if update.action == "modify" and update.modified_plan:
                plan = update.modified_plan
                self.logger.info("Plan modified by engine")

            # Clear step-specific context after step completion
            set_logging_context(actor_name=None, step_id=None)

        # Mark as completed
        plan.status = "COMPLETED"
        current_status = await self._transition_status(
            repo, process_id, plan, context, current_status, ProcessStatus.COMPLETED
        )

        self._emit_event("process_completed", "Process completed successfully")
        self.logger.info("Process completed successfully")

        return ProcessResult(
            process_id=process_id,
            status=current_status,
            plan=plan,
            context=context.to_dict(),
            step_results=step_results,
        )

    async def _transition_status(
        self,
        repo: ProcessRepository,
        process_id: uuid.UUID,
        plan: Plan,
        context: TypedContext,
        from_status: ProcessStatus,
        to_status: ProcessStatus,
    ) -> ProcessStatus:
        """
        Transition process to a new status with validation.

        Args:
            repo: Process repository
            process_id: Process ID
            plan: Current plan
            context: Current context
            from_status: Current status
            to_status: Target status

        Returns:
            New status after transition

        Raises:
            InvalidTransitionError: If transition is not valid
        """
        ProcessStateMachine.validate_transition(from_status, to_status)

        await repo.update_process(
            process_id=process_id,
            plan=plan,
            context=context.to_dict(),
            status=to_status,
        )

        self.logger.info(
            f"Process transitioned: {from_status.value} -> {to_status.value}"
        )
        return to_status

    def _emit_event(
        self,
        action_type: str,
        message: str,
        status: str = "complete",
    ) -> None:
        """
        Emit an event to the EventBus.

        Args:
            action_type: Type of action (e.g., "step_completed")
            message: Human-readable message
            status: "complete" or "error"
        """
        action = AgentAction(
            agentId="Orchestrator",
            actionType=action_type,
            message=message,
            status=status,  # type: ignore[arg-type]
        )
        self.event_bus.emit(action)
