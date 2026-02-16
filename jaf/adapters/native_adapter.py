"""
JAF NativeAdapter — OpenAI Responses API Engine
=================================================

Implements the agentic loop using OpenAI's Responses API with function calling.
This is the real engine that gives agents intelligence: the LLM decides which
tools to call, in what order, based on the goal and the data it receives.

Uses the modern Responses API (client.responses.create) instead of the older
Chat Completions API, enabling:
  - Stateful conversations via previous_response_id
  - Native tool orchestration
  - Support for GPT-5 family models (gpt-5-nano, gpt-5-mini, gpt-5.2)

Event emission at every step ensures the frontend sees real-time reasoning:
  thinking → tool_called → tool_result → … → completed

Usage:
    adapter = NativeAdapter(model="gpt-5-nano")
    result = await adapter.run(goal, actors, context, process_id)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jaf.core.actor import Actor, Tool

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class NativeAdapter:
    """
    OpenAI Responses API engine for JAF actors.

    Unlike the deterministic NativeEngine in framework/, this adapter
    uses the LLM to *decide* which tools to call. The loop:

      1. Build instructions with actor/tool context
      2. Send to OpenAI Responses API (with tool schemas)
      3. If LLM returns function_call items → execute each, feed results back
      4. If LLM returns text → agent is done
      5. Emit events at every step for real-time UI
    """

    def __init__(
        self,
        model: str = "gpt-5-nano",
        temperature: float = 0.8,
        max_iterations: int = 15,
    ):
        self.model = model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self._client = None  # lazy init

    def _get_client(self):
        """Lazy-init the OpenAI async client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI()
        return self._client

    def _build_instructions(self, actors: List[Actor], context: Dict[str, Any]) -> str:
        """Build instructions that describe available actors and context."""
        actor_descriptions = []
        for actor in actors:
            tools_desc = ", ".join(
                f"{t.name} ({t.description})" for t in actor.tools
            )
            actor_descriptions.append(
                f"- {actor.name}: {actor.description}\n  Tools: {tools_desc}"
            )

        context_str = ""
        if context:
            context_str = "\n\nBusiness Context:\n" + json.dumps(context, indent=2, default=str)

        return (
            "You are an intelligent agent in the JAF (Jems AI Framework) orchestration system.\n"
            "You have access to specialized tools provided by actors. Use them to accomplish the goal.\n\n"
            "IMPORTANT INSTRUCTIONS:\n"
            "- Call tools to gather data before making decisions\n"
            "- Analyze the data you receive carefully\n"
            "- Make specific, data-driven recommendations\n"
            "- When you have enough information, provide a clear summary with your findings\n"
            "- Be concise but thorough\n\n"
            f"Available Actors:\n" + "\n".join(actor_descriptions) + context_str
        )

    def _build_tool_schemas(self, actors: List[Actor]) -> tuple[List[dict], Dict[str, tuple[Actor, Tool]]]:
        """
        Build Responses API tool schemas and a lookup map.

        Returns:
            (openai_tools, tool_lookup) where tool_lookup maps
            "actor_name__tool_name" → (actor, tool) for execution dispatch.
        """
        openai_tools = []
        tool_lookup: Dict[str, tuple[Actor, Tool]] = {}

        for actor in actors:
            for tool in actor.tools:
                schema = tool.to_schema()
                qualified_name = f"{actor.name}__{tool.name}"
                # Responses API format: type/name/description/parameters at top level
                openai_tool = {
                    "type": "function",
                    "name": qualified_name,
                    "description": f"[{actor.name}] {schema.get('description', '')}",
                    "parameters": schema.get("parameters", {"type": "object", "properties": {}}),
                }
                openai_tools.append(openai_tool)
                tool_lookup[qualified_name] = (actor, tool)

        return openai_tools, tool_lookup

    # ------------------------------------------------------------------
    # Multi-Agent: true delegation (orchestrator → sub-agents → synthesis)
    # ------------------------------------------------------------------

    async def run_multi_agent(
        self,
        goal: str,
        actors: List[Actor],
        context: Optional[Dict[str, Any]] = None,
        process_id: Optional[str] = None,
        event_callback: Optional[Any] = None,
        planning_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run a true multi-agent workflow with delegation.

        Phase 1 — PLANNING: An orchestrator LLM receives the goal and the
                  list of available agents + their capabilities, then produces
                  a delegation plan (which agent handles what sub-goal).
        Phase 2 — DELEGATION: For each delegation step the designated agent
                  gets its own independent NativeAdapter.run() call with only
                  *its* tools.  Events are emitted under that agent's name.
        Phase 3 — SYNTHESIS: The orchestrator LLM receives all sub-agent
                  results and produces a unified final answer.

        Args:
            planning_model: Optional model override for planning/synthesis
                           (e.g. gpt-5-mini for better reasoning)
        """
        context = context or {}
        process_id = process_id or str(uuid.uuid4())
        orch_model = planning_model or self.model

        async def emit(event_type: str, **kwargs):
            event = {
                "process_id": process_id,
                "actionType": event_type,
                "timestamp": _now_iso(),
                **kwargs,
            }
            if event_callback:
                try:
                    if asyncio.iscoroutinefunction(event_callback):
                        await event_callback(event)
                    else:
                        event_callback(event)
                except Exception as e:
                    logger.warning(f"Event callback error: {e}")

        await emit(
            "process_started",
            agentId="orchestrator",
            status="complete",
            message=f"Multi-Agent Orchestrator — {goal}",
            data={
                "goal": goal,
                "agents": [a.name for a in actors],
                "model": self.model,
                "planning_model": orch_model,
                "engine": "NativeAdapter (Multi-Agent)",
            },
        )

        client = self._get_client()

        # ── Phase 1: PLANNING ─────────────────────────────────────
        agent_descriptions = []
        for actor in actors:
            tools_desc = ", ".join(f"{t.name} ({t.description})" for t in actor.tools)
            agent_descriptions.append(
                f"- {actor.name}: {actor.description}\n  Tools: {tools_desc}"
            )

        context_str = ""
        if context:
            context_str = "\n\nBusiness Context:\n" + json.dumps(context, indent=2, default=str)

        planning_instructions = (
            "You are a multi-agent orchestrator. You have specialized agents, "
            "each with their own tools and expertise.\n\n"
            "Your job is to DELEGATE parts of the goal to the right agents. "
            "Each agent will work independently with its own tools.\n\n"
            f"Available Agents:\n" + "\n".join(agent_descriptions) + context_str + "\n\n"
            "Return a JSON object with a 'steps' array. Each step assigns a sub-goal "
            "to one agent. Example:\n"
            '{"steps": [{"agent": "AgentName", "sub_goal": "What this agent should do"}]}\n\n'
            "Rules:\n"
            "- Use EVERY agent at least once if relevant\n"
            "- Sub-goals should be specific and actionable\n"
            "- Order matters: put data-gathering first, analysis second\n"
        )

        await emit(
            "thinking",
            agentId="orchestrator",
            status="complete",
            message=f"Planning delegation with {orch_model}...",
            data={"phase": "planning", "model": orch_model},
        )

        t0 = time.monotonic()
        planning_response = await client.responses.create(
            model=orch_model,
            instructions=planning_instructions,
            input=[{"role": "user", "content": f"Goal: {goal}\n\nRespond with a JSON object."}],
            text={"format": {"type": "json_object"}},
        )
        plan_ms = int((time.monotonic() - t0) * 1000)

        plan_text = planning_response.output_text or "[]"

        await emit(
            "llm_response",
            agentId="orchestrator",
            status="complete",
            message=f"Delegation plan created in {plan_ms}ms ({orch_model})",
            data={"latency_ms": plan_ms, "phase": "planning"},
        )

        # Parse delegation plan
        try:
            plan_data = json.loads(plan_text)
            if isinstance(plan_data, dict):
                delegations = plan_data.get("steps") or plan_data.get("delegations") or list(plan_data.values())[0]
            else:
                delegations = plan_data
        except (json.JSONDecodeError, IndexError):
            delegations = [{"agent": a.name, "sub_goal": goal} for a in actors]

        # ── Phase 2: DELEGATION ───────────────────────────────────
        actor_map = {a.name: a for a in actors}
        sub_results = []

        for i, delegation in enumerate(delegations):
            agent_name = delegation.get("agent", "")
            sub_goal = delegation.get("sub_goal", goal)

            agent = actor_map.get(agent_name)
            if not agent:
                for name, a in actor_map.items():
                    if agent_name.lower() in name.lower() or name.lower() in agent_name.lower():
                        agent = a
                        break
            if not agent:
                await emit(
                    "tool_error",
                    agentId="orchestrator",
                    status="error",
                    message=f"Unknown agent '{agent_name}', skipping delegation step",
                    data={"delegation": delegation},
                )
                continue

            await emit(
                "tool_called",
                agentId="orchestrator",
                status="complete",
                message=f"Delegating to {agent.name}: {sub_goal}",
                data={"agent": agent.name, "sub_goal": sub_goal, "delegation_step": i + 1},
            )

            sub_adapter = NativeAdapter(
                model=self.model,
                max_iterations=8,
            )
            sub_adapter._client = self._client

            sub_result = await sub_adapter.run(
                goal=sub_goal,
                actors=[agent],
                context=context,
                process_id=process_id,
                event_callback=event_callback,
            )

            sub_results.append({
                "agent": agent.name,
                "sub_goal": sub_goal,
                "result": sub_result.get("result", "No result"),
            })

            await emit(
                "tool_result",
                agentId="orchestrator",
                status="complete",
                message=f"{agent.name} completed its delegation",
                data={"agent": agent.name, "delegation_step": i + 1},
            )

        # ── Phase 3: SYNTHESIS ────────────────────────────────────
        await emit(
            "thinking",
            agentId="orchestrator",
            status="complete",
            message=f"Synthesizing results with {orch_model}...",
            data={"phase": "synthesis"},
        )

        synthesis_instructions = (
            "You are a multi-agent orchestrator synthesizing results from specialized agents.\n\n"
            "Each agent worked independently on a sub-goal. Combine their findings into a "
            "unified, coherent final response.\n\n"
            "Agent Results:\n"
        )
        for sr in sub_results:
            synthesis_instructions += f"\n--- {sr['agent']} (sub-goal: {sr['sub_goal']}) ---\n{sr['result']}\n"

        synthesis_instructions += (
            "\n\nProvide a unified assessment that:\n"
            "1. Highlights the key findings from each agent\n"
            "2. Identifies connections between the findings\n"
            "3. Gives clear, actionable recommendations\n"
        )

        t0 = time.monotonic()
        synthesis_response = await client.responses.create(
            model=orch_model,
            instructions=synthesis_instructions,
            input=[{"role": "user", "content": f"Original goal: {goal}"}],
        )
        synth_ms = int((time.monotonic() - t0) * 1000)

        final_result = synthesis_response.output_text or "Synthesis failed."

        await emit(
            "completed",
            agentId="orchestrator",
            status="complete",
            message="Multi-agent workflow completed",
            data={
                "result": final_result,
                "total_delegations": len(sub_results),
                "agents_used": [sr["agent"] for sr in sub_results],
            },
        )

        return {
            "result": final_result,
            "sub_results": sub_results,
            "delegations": len(sub_results),
            "model": self.model,
            "planning_model": orch_model,
            "process_id": process_id,
        }

    # ------------------------------------------------------------------
    # Dynamic Orchestrator: adaptive re-planning with persistence
    # ------------------------------------------------------------------

    async def run_dynamic(
        self,
        goal: str,
        actors: List[Actor],
        context: Optional[Dict[str, Any]] = None,
        process_id: Optional[str] = None,
        event_callback: Optional[Any] = None,
        planning_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run a dynamic orchestration workflow with adaptive re-planning.

        Phases:
          1. DISCOVERY — enumerate actors and their capabilities from the registry
          2. PLANNING  — LLM creates an initial step-by-step plan
          3. EXECUTION — execute each step, evaluate, and optionally add new steps
          4. SYNTHESIS  — produce a unified final report

        The orchestrator can talk to agents and agents report back, but agents
        never communicate directly with each other (Actor model).

        Returns enriched result dict including plan_history and step details.
        """
        context = context or {}
        process_id = process_id or str(uuid.uuid4())
        orch_model = planning_model or self.model

        async def emit(event_type: str, **kwargs):
            event = {
                "process_id": process_id,
                "actionType": event_type,
                "timestamp": _now_iso(),
                **kwargs,
            }
            if event_callback:
                try:
                    if asyncio.iscoroutinefunction(event_callback):
                        await event_callback(event)
                    else:
                        event_callback(event)
                except Exception as e:
                    logger.warning(f"Event callback error: {e}")

        # Wrapper to suppress terminal events from sub-step NativeAdapter runs
        async def _step_cb(event: dict):
            action = event.get("actionType", "")
            if action in ("completed", "error"):
                event = dict(event)
                event["actionType"] = "tool_result"
                event["data"] = event.get("data", {})
                event["data"]["_original_type"] = action
            if event_callback:
                if asyncio.iscoroutinefunction(event_callback):
                    await event_callback(event)
                else:
                    event_callback(event)

        client = self._get_client()

        # ── PHASE 1: DISCOVERY ──────────────────────────────────
        await emit(
            "thinking",
            agentId="orchestrator",
            status="complete",
            message="Phase 1: Dynamic Agent Discovery — querying ActorRegistry...",
            data={"phase": "discovery"},
        )

        agent_catalog = []
        for actor in actors:
            tools_desc = [f"{t.name}: {t.description}" for t in actor.tools]
            agent_catalog.append({
                "name": actor.name,
                "description": actor.description,
                "tools": [t.name for t in actor.tools],
                "tool_details": tools_desc,
            })
            await emit(
                "tool_result",
                agentId="orchestrator",
                status="complete",
                message=f"Discovered: {actor.name} ({len(actor.tools)} tools: {', '.join(t.name for t in actor.tools)})",
                data={"phase": "discovery", "agent": actor.name},
            )

        await emit(
            "llm_response",
            agentId="orchestrator",
            status="complete",
            message=f"Discovery complete: {len(actors)} agents, {sum(len(a['tools']) for a in agent_catalog)} tools available",
            data={"phase": "discovery", "total_agents": len(actors)},
        )

        # ── PHASE 2: INITIAL PLANNING ──────────────────────────
        await emit(
            "thinking",
            agentId="orchestrator",
            status="complete",
            message=f"Phase 2: Dynamic Planning with {orch_model}...",
            data={"phase": "planning", "model": orch_model},
        )

        catalog_str = "\n".join(
            f"- {a['name']}: {a['description']}\n  Tools: {', '.join(a['tool_details'])}"
            for a in agent_catalog
        )
        context_str = json.dumps(context, indent=2, default=str) if context else "None"

        planning_prompt = (
            "You are a dynamic AI orchestrator. You discover available agents at runtime "
            "and create adaptive execution plans.\n\n"
            "DISCOVERED AGENTS:\n" + catalog_str + "\n\n"
            "BUSINESS CONTEXT:\n" + context_str + "\n\n"
            "RULES:\n"
            "- Create an initial plan of 3-5 steps\n"
            "- Each step must specify which agent to use and what to do\n"
            "- Flag steps where results might trigger follow-up investigation\n"
            "- Steps should build on each other logically\n\n"
            "Return a JSON object with a 'plan' array. Each step has:\n"
            "  - step (number)\n"
            "  - agent (agent name from discovered list)\n"
            "  - description (what to do)\n"
            "  - may_trigger_replan (boolean)\n"
        )

        t0 = time.monotonic()
        plan_response = await client.responses.create(
            model=orch_model,
            instructions=planning_prompt,
            input=[{"role": "user", "content": f"Goal: {goal}\n\nRespond with a JSON object."}],
            text={"format": {"type": "json_object"}},
        )
        plan_ms = int((time.monotonic() - t0) * 1000)

        plan_text = plan_response.output_text or '{"plan": []}'
        try:
            plan_data = json.loads(plan_text)
            steps = plan_data.get("plan") or plan_data.get("steps") or []
        except json.JSONDecodeError:
            steps = [{"step": 1, "agent": actors[0].name, "description": goal, "may_trigger_replan": False}]

        # Emit plan
        await emit(
            "llm_response",
            agentId="orchestrator",
            status="complete",
            message=f"Initial plan: {len(steps)} steps created in {plan_ms}ms ({orch_model})",
            data={"phase": "planning", "latency_ms": plan_ms, "steps": len(steps)},
        )
        for i, step in enumerate(steps):
            replan_flag = " [may trigger re-plan]" if step.get("may_trigger_replan") else ""
            await emit(
                "tool_result",
                agentId="orchestrator",
                status="complete",
                message=f"Step {i+1}: [{step.get('agent', '?')}] {step.get('description', '?')}{replan_flag}",
                data={"phase": "planning", "step": i + 1},
            )

        # ── Persistence callback hook ───────────────────────────
        # The demo runner injects persistence via on_plan_created / on_step_completed etc.
        # Here we just call the event callback with structured data so the demo can persist.

        await emit(
            "plan_created",
            agentId="orchestrator",
            status="complete",
            message=f"Plan created: {len(steps)} steps",
            data={"phase": "planning", "plan": steps},
        )

        # ── PHASE 3: ADAPTIVE EXECUTION ─────────────────────────
        await emit(
            "thinking",
            agentId="orchestrator",
            status="complete",
            message=f"Phase 3: Adaptive Execution with {self.model}...",
            data={"phase": "executing"},
        )

        step_results = []
        agent_map = {a.name: a for a in actors}
        total_steps_executed = 0
        steps_added = 0
        plan_history = [{"version": 1, "steps": list(steps)}]

        MAX_TOTAL_STEPS = 8   # hard cap on total steps (including dynamic)
        MAX_REPLANS = 2       # hard cap on re-planning rounds

        step_idx = 0
        replan_count = 0
        while step_idx < len(steps) and total_steps_executed < MAX_TOTAL_STEPS:
            step = steps[step_idx]
            step_num = step_idx + 1
            step_desc = step.get("description", f"Step {step_num}")
            step_agent_name = step.get("agent", "")

            # ── Orchestrator → Agent ──
            await emit(
                "tool_called",
                agentId="orchestrator",
                status="complete",
                message=f"Orchestrator → {step_agent_name}: \"{step_desc}\"",
                data={"phase": "executing", "step": step_num, "total_steps": len(steps), "direction": "orchestrator→agent"},
            )

            # Find agent
            target_agent = agent_map.get(step_agent_name)
            if not target_agent:
                for name, a in agent_map.items():
                    if step_agent_name.lower() in name.lower() or name.lower() in step_agent_name.lower():
                        target_agent = a
                        break
            step_actors = [target_agent] if target_agent else actors

            # Build focused goal with prior context
            prior_context = ""
            if step_results:
                prior_context = "\n\nResults from previous steps:\n"
                for prev in step_results[-3:]:
                    prior_context += f"- Step {prev['step']}: {prev['result'][:300]}\n"

            step_goal = f"{step_desc}{prior_context}"

            # Execute via NativeAdapter.run()
            step_adapter = NativeAdapter(model=self.model, max_iterations=6)
            step_adapter._client = client

            step_result = await step_adapter.run(
                goal=step_goal,
                actors=step_actors,
                context=context,
                process_id=process_id,
                event_callback=_step_cb,
            )

            result_text = step_result.get("result", "No result")
            total_steps_executed += 1

            # ── Agent → Orchestrator ──
            await emit(
                "tool_result",
                agentId=step_agent_name or "engine",
                status="complete",
                message=f"{step_agent_name or 'Agent'} → Orchestrator: step {step_num} complete",
                data={"phase": "executing", "step": step_num, "direction": "agent→orchestrator"},
            )

            step_results.append({
                "step": step_num,
                "agent": step_agent_name,
                "description": step_desc,
                "result": result_text,
                "tool_calls": len(step_result.get("tool_calls_made", [])),
            })

            # Emit step_completed for persistence
            await emit(
                "step_completed",
                agentId=step_agent_name or "engine",
                status="complete",
                message=f"Step {step_num} completed by {step_agent_name}",
                data={"phase": "executing", "step": step_num, "agent": step_agent_name, "result_preview": result_text[:500]},
            )

            # ── DYNAMIC RE-PLANNING ──
            can_replan = replan_count < MAX_REPLANS and total_steps_executed < MAX_TOTAL_STEPS - 1
            if can_replan and (step.get("may_trigger_replan") or step_idx == len(steps) - 2):
                await emit(
                    "thinking",
                    agentId="orchestrator",
                    status="complete",
                    message=f"Evaluating step {step_num} — checking if re-planning needed...",
                    data={"phase": "re-planning", "step": step_num},
                )

                replan_prompt = (
                    "You are a dynamic orchestrator evaluating execution progress.\n\n"
                    f"Original goal: {goal}\n\n"
                    f"Steps completed so far:\n"
                )
                for sr in step_results:
                    replan_prompt += f"  Step {sr['step']} [{sr['agent']}]: {sr['description']}\n    Result: {sr['result'][:400]}\n\n"
                remaining = [s.get("description", "?") for s in steps[step_idx + 1:]]
                replan_prompt += f"Remaining planned steps: {remaining if remaining else 'None'}\n\n"
                replan_prompt += (
                    "Based on what you've discovered, do you need to ADD new steps?\n"
                    "Return a JSON object:\n"
                    "- 'needs_new_steps': boolean\n"
                    "- 'new_steps': array of new steps (each with 'agent', 'description', 'may_trigger_replan')\n"
                    "- 'reason': why you're adding or not adding steps\n\n"
                    "Only add steps if the results reveal something unexpected.\n"
                )

                t0 = time.monotonic()
                replan_response = await client.responses.create(
                    model=orch_model,
                    instructions=replan_prompt,
                    input=[{"role": "user", "content": "Evaluate and decide on re-planning. Respond with a JSON object."}],
                    text={"format": {"type": "json_object"}},
                )
                replan_ms = int((time.monotonic() - t0) * 1000)
                replan_text = replan_response.output_text or '{"needs_new_steps": false}'

                try:
                    replan_data = json.loads(replan_text)
                except json.JSONDecodeError:
                    replan_data = {"needs_new_steps": False, "reason": "Parse error"}

                if replan_data.get("needs_new_steps") and replan_data.get("new_steps"):
                    new_steps = replan_data["new_steps"]
                    reason = replan_data.get("reason", "New investigation needed")
                    for j, ns in enumerate(new_steps):
                        ns["step"] = len(steps) + j + 1
                        steps.append(ns)
                    steps_added += len(new_steps)
                    replan_count += 1
                    plan_history.append({"version": len(plan_history) + 1, "steps_added": new_steps, "reason": reason})

                    await emit(
                        "plan_updated",
                        agentId="orchestrator",
                        status="complete",
                        message=f"RE-PLAN: Added {len(new_steps)} new steps — {reason}",
                        data={"phase": "re-planning", "new_steps": len(new_steps), "total_steps": len(steps), "reason": reason, "plan": steps},
                    )
                    for ns in new_steps:
                        await emit(
                            "tool_result",
                            agentId="orchestrator",
                            status="complete",
                            message=f"New step: [{ns.get('agent', '?')}] {ns.get('description', '?')}",
                            data={"phase": "re-planning"},
                        )
                else:
                    reason = replan_data.get("reason", "Plan is sufficient")
                    await emit(
                        "llm_response",
                        agentId="orchestrator",
                        status="complete",
                        message=f"No re-planning needed: {reason}",
                        data={"phase": "re-planning", "reason": reason},
                    )

            step_idx += 1

        # ── PHASE 4: SYNTHESIS ──────────────────────────────────
        await emit(
            "thinking",
            agentId="orchestrator",
            status="complete",
            message=f"Phase 4: Synthesizing findings with {orch_model}...",
            data={"phase": "synthesis"},
        )

        synth_prompt = (
            "You are an AI orchestrator synthesizing the results of a dynamic, adaptive investigation.\n\n"
            f"Original Goal: {goal}\n\n"
            f"Execution Summary:\n"
            f"- Agents discovered: {len(actors)}\n"
            f"- Initial plan: {len(steps) - steps_added} steps\n"
            f"- Steps added dynamically: {steps_added}\n"
            f"- Total steps executed: {total_steps_executed}\n\n"
            "Step Results:\n"
        )
        for sr in step_results:
            synth_prompt += f"\n--- Step {sr['step']} [{sr['agent']}]: {sr['description']} ---\n{sr['result'][:800]}\n"

        synth_prompt += (
            "\n\nProvide a comprehensive final report that:\n"
            "1. Summarizes key findings from each phase\n"
            "2. Highlights discoveries that triggered dynamic re-planning\n"
            "3. Gives actionable recommendations\n"
            "4. Notes the audit trail (all steps persisted to database)\n"
        )

        t0 = time.monotonic()
        synth_response = await client.responses.create(
            model=orch_model,
            instructions=synth_prompt,
            input=[{"role": "user", "content": f"Synthesize: {goal}"}],
        )
        synth_ms = int((time.monotonic() - t0) * 1000)
        final_result = synth_response.output_text or "Synthesis failed."

        await emit(
            "completed",
            agentId="orchestrator",
            status="complete",
            message="Dynamic Orchestrator completed with full audit trail",
            data={
                "result": final_result,
                "total_steps": total_steps_executed,
                "steps_added": steps_added,
                "plan_history": plan_history,
                "step_results": step_results,
                "process_id": process_id,
            },
        )

        return {
            "result": final_result,
            "step_results": step_results,
            "plan_steps": len(steps),
            "steps_added": steps_added,
            "total_executed": total_steps_executed,
            "plan_history": plan_history,
            "planning_model": orch_model,
            "execution_model": self.model,
            "model": self.model,
            "process_id": process_id,
        }

    # ------------------------------------------------------------------
    # Single-Agent: agentic loop with function calling (Responses API)
    # ------------------------------------------------------------------

    async def run(
        self,
        goal: str,
        actors: List[Actor],
        context: Optional[Dict[str, Any]] = None,
        process_id: Optional[str] = None,
        event_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Run the agentic loop using the Responses API.

        Args:
            goal: What the agent should accomplish
            actors: List of Actor instances with tools
            context: Optional business context / data
            process_id: Optional process ID for event correlation
            event_callback: Optional async callable(event_dict) for emitting events

        Returns:
            Dict with 'result', 'tool_calls_made', 'iterations', 'model'
        """
        context = context or {}
        process_id = process_id or str(uuid.uuid4())

        async def emit(event_type: str, **kwargs):
            """Emit an event through the callback."""
            event = {
                "process_id": process_id,
                "actionType": event_type,
                "timestamp": _now_iso(),
                **kwargs,
            }
            if event_callback:
                try:
                    if asyncio.iscoroutinefunction(event_callback):
                        await event_callback(event)
                    else:
                        event_callback(event)
                except Exception as e:
                    logger.warning(f"Event callback error: {e}")

        # Build instructions and tool schemas
        instructions = self._build_instructions(actors, context)
        openai_tools, tool_lookup = self._build_tool_schemas(actors)

        # Initial input
        input_items: list = [
            {"role": "user", "content": f"Goal: {goal}"},
        ]

        await emit(
            "process_started",
            agentId="engine",
            status="complete",
            message=f"Responses API ({self.model}) — {goal}",
            data={"goal": goal, "actors": [a.name for a in actors], "model": self.model, "engine": "NativeAdapter"},
        )

        client = self._get_client()
        tool_calls_made = []
        iteration = 0

        try:
            while iteration < self.max_iterations:
                iteration += 1

                await emit(
                    "thinking",
                    agentId="engine",
                    status="complete",
                    message=f"Analyzing situation (iteration {iteration})...",
                    data={"iteration": iteration},
                )

                # ── Call Responses API ──
                t0 = time.monotonic()
                response = await client.responses.create(
                    model=self.model,
                    instructions=instructions,
                    input=input_items,
                    tools=openai_tools if openai_tools else [],
                )
                latency_ms = int((time.monotonic() - t0) * 1000)

                usage = response.usage
                tokens_str = f"{usage.total_tokens} tokens" if usage else "? tokens"

                await emit(
                    "llm_response",
                    agentId="engine",
                    status="complete",
                    message=f"LLM responded in {latency_ms}ms ({tokens_str})",
                    data={
                        "latency_ms": latency_ms,
                        "input_tokens": usage.input_tokens if usage else 0,
                        "output_tokens": usage.output_tokens if usage else 0,
                        "total_tokens": usage.total_tokens if usage else 0,
                    },
                )

                # ── Check for function calls in output ──
                function_calls = [
                    item for item in response.output
                    if item.type == "function_call"
                ]

                if not function_calls:
                    # No tool calls → agent is done
                    final_content = response.output_text or "No response generated."

                    await emit(
                        "completed",
                        agentId="engine",
                        status="complete",
                        message="Agent finished with final response.",
                        data={
                            "result": final_content,
                            "total_iterations": iteration,
                            "total_tool_calls": len(tool_calls_made),
                        },
                    )

                    return {
                        "result": final_content,
                        "tool_calls_made": tool_calls_made,
                        "iterations": iteration,
                        "model": self.model,
                        "process_id": process_id,
                    }

                # ── Execute tool calls ──
                # Add ALL output items (including reasoning) to input for next turn
                # This is required for reasoning models (GPT-5, o4-mini)
                input_items += response.output

                for fc in function_calls:
                    fn_name = fc.name
                    try:
                        fn_args = json.loads(fc.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}

                    if fn_name not in tool_lookup:
                        error_msg = f"Unknown tool: {fn_name}"
                        await emit(
                            "tool_error",
                            agentId="engine",
                            status="error",
                            message=error_msg,
                            data={"tool": fn_name, "error": error_msg},
                        )
                        input_items.append({
                            "type": "function_call_output",
                            "call_id": fc.call_id,
                            "output": json.dumps({"error": error_msg}),
                        })
                        continue

                    actor_instance, tool_instance = tool_lookup[fn_name]

                    await emit(
                        "tool_called",
                        agentId=actor_instance.name,
                        status="complete",
                        message=f"Calling {actor_instance.name}.{tool_instance.name}({json.dumps(fn_args)})",
                        data={
                            "actor": actor_instance.name,
                            "tool": tool_instance.name,
                            "arguments": fn_args,
                        },
                    )

                    # Execute the tool
                    t1 = time.monotonic()
                    try:
                        result = await actor_instance.execute(tool_instance.name, fn_args)
                        exec_ms = int((time.monotonic() - t1) * 1000)

                        if isinstance(result, (dict, list)):
                            result_str = json.dumps(result, indent=2, default=str)
                        else:
                            result_str = str(result)

                        tool_calls_made.append({
                            "actor": actor_instance.name,
                            "tool": tool_instance.name,
                            "arguments": fn_args,
                            "result_preview": result_str[:500],
                            "execution_ms": exec_ms,
                        })

                        await emit(
                            "tool_result",
                            agentId=actor_instance.name,
                            status="complete",
                            message=f"{tool_instance.name} returned data ({exec_ms}ms)",
                            data={
                                "actor": actor_instance.name,
                                "tool": tool_instance.name,
                                "result": result_str[:2000],
                                "execution_ms": exec_ms,
                            },
                        )

                        input_items.append({
                            "type": "function_call_output",
                            "call_id": fc.call_id,
                            "output": result_str,
                        })

                    except Exception as e:
                        exec_ms = int((time.monotonic() - t1) * 1000)
                        error_msg = f"Tool execution failed: {str(e)}"

                        await emit(
                            "tool_error",
                            agentId=actor_instance.name,
                            status="error",
                            message=error_msg,
                            data={
                                "actor": actor_instance.name,
                                "tool": tool_instance.name,
                                "error": str(e),
                                "execution_ms": exec_ms,
                            },
                        )

                        input_items.append({
                            "type": "function_call_output",
                            "call_id": fc.call_id,
                            "output": json.dumps({"error": str(e)}),
                        })

            # Max iterations reached
            await emit(
                "completed",
                agentId="engine",
                status="complete",
                message=f"Max iterations ({self.max_iterations}) reached.",
                data={"total_iterations": iteration, "total_tool_calls": len(tool_calls_made)},
            )

            return {
                "result": "Max iterations reached. Partial results available in tool call history.",
                "tool_calls_made": tool_calls_made,
                "iterations": iteration,
                "model": self.model,
                "process_id": process_id,
            }

        except Exception as e:
            await emit(
                "error",
                agentId="engine",
                status="error",
                message=f"Engine error: {str(e)}",
                data={"error": str(e), "iteration": iteration},
            )
            raise
