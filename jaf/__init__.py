"""
JAF - Jems Agent Framework

A hybrid neuro-symbolic automation framework based on the Actor Model.
Supports three execution modes: Agentic, Multi-Agent, and Traditional Automation.

Author: Orange Innovation Team
Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "Orange Innovation Team"

from jaf.core.models import (
    ProcessState,
    ExecutionMode,
    LLMConfig,
    Plan,
    PlanStep,
    StepResult,
    Process,
)
from jaf.core.actor import Actor, ActorRegistry, Tool, actor
from jaf.core.engine import EngineAbstraction

__all__ = [
    # Version
    "__version__",
    # Models
    "ProcessState",
    "ExecutionMode",
    "LLMConfig",
    "Plan",
    "PlanStep",
    "StepResult",
    "Process",
    # Core
    "Actor",
    "ActorRegistry",
    "Tool",
    "actor",
    "EngineAbstraction",
]

