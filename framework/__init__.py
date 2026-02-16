"""
Core framework components for building and orchestrating AI agents.
"""

# Expose CLI
from .cli import app as cli

__all__ = ["cli"]

# =============================================================================
# Version
# =============================================================================
from framework._version import __version__, __version_info__

# =============================================================================
# Types
# =============================================================================
from framework.types import (
    LLMConfig,
    Plan,
    PlanStep,
    PlanUpdate,
    StepResult,
    AgentAction,
)

# =============================================================================
# Actor
# =============================================================================
from framework.actor import Actor, ActorRegistry

# =============================================================================
# Engine
# =============================================================================
from framework.engine import (
    EngineAbstraction,
    NativeEngine,
    CrewAIAdapter,
    EngineFactory,
)

# =============================================================================
# Orchestration
# =============================================================================
from framework.orchestrator import Orchestrator
from framework.state_machine import ProcessStateMachine

# =============================================================================
# Events
# =============================================================================
from framework.event_bus import EventBus, get_event_bus, console_subscriber

# =============================================================================
# Data Contracts & Validation
# =============================================================================
from framework.data import (
    DataContract,
    DataEnvelope,
    SchemaRegistry,
    DataValidationError,
    TypedContext,
)

# =============================================================================
# Tool Contracts
# =============================================================================
from framework.tools import tool_contract, ToolContract

# =============================================================================
# Persistence
# =============================================================================
from framework.persistence import ProcessStatus, ProcessSchema

# =============================================================================
# Observability
# =============================================================================
from framework.observability.telemetry import TokenUsage, TelemetryCalculator

# =============================================================================
# Exceptions
# =============================================================================
from framework.exceptions import FrameworkException, EngineException

# =============================================================================
# Public API
# =============================================================================
__all__ = [
    # Version
    "__version__",
    "__version_info__",
    # Types
    "LLMConfig",
    "Plan",
    "PlanStep",
    "PlanUpdate",
    "StepResult",
    "AgentAction",
    # Actor
    "Actor",
    "ActorRegistry",
    # Engine
    "EngineAbstraction",
    "NativeEngine",
    "CrewAIAdapter",
    "EngineFactory",
    # Orchestration
    "Orchestrator",
    "ProcessStateMachine",
    # Events
    "EventBus",
    "get_event_bus",
    "console_subscriber",
    # Data Contracts & Validation
    "DataContract",
    "DataEnvelope",
    "SchemaRegistry",
    "DataValidationError",
    "TypedContext",
    # Tool Contracts
    "tool_contract",
    "ToolContract",
    # Persistence
    "ProcessStatus",
    "ProcessSchema",
    # Observability
    "TokenUsage",
    "TelemetryCalculator",
    # Exceptions
    "FrameworkException",
    "EngineException",
]
