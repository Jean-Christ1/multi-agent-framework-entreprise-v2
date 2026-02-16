"""
Engine module for the JAF framework.

Exports:
- EngineAbstraction: ABC for all engine adapters
- CrewAIAdapter: CrewAI-based engine implementation
- NativeEngine: Deterministic engine without LLM dependencies
"""

from framework.engine.engine_abstraction import EngineAbstraction
from framework.engine.crewai_adapter import CrewAIAdapter
from framework.engine.native_engine import NativeEngine
from framework.engine.factory import EngineFactory

__all__ = ["EngineAbstraction", "CrewAIAdapter", "NativeEngine", "EngineFactory"]
