"""
Typed entities shared across planner implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OrchestrationIntent:
    """Represents the high-level goal submitted by a user."""

    prompt: str
    scenario: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlannerContext:
    """Provides runtime state to planners."""

    orchestrator: Any
    discovery: Dict[str, Any] = field(default_factory=dict)
    memory_context: Optional[Dict[str, Any]] = None
    step_callback: Optional[Any] = None
    start_time_ms: Optional[float] = None
    trace_id: Optional[str] = None


@dataclass
class PlanGraph:
    """Lightweight plan abstraction for deterministic and LLM-driven planners."""

    name: str
    description: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionReport:
    """Normalized response returned by planner executions."""

    answer: str
    plan: PlanGraph
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
