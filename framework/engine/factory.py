from __future__ import annotations

from typing import List, Optional

from framework.actor.base_actor import Actor
from framework.engine.crewai_adapter import CrewAIAdapter
from framework.engine.vertexai_adapter import VertexAIAdapter
from framework.engine.native_engine import NativeEngine
from framework.logging import get_logger

logger = get_logger(__name__)


def create_engine(engine_type: str, **kwargs):
    """
    Backwards-compatible engine constructor (kept because it may be used elsewhere).

    Supported:
      - crewai   -> CrewAIAdapter(**kwargs)
      - vertexai -> VertexAIAdapter(**kwargs)
      - native   -> NativeEngine()
    """
    et = engine_type.lower().strip()

    if et == "crewai":
        return CrewAIAdapter(**kwargs)

    if et == "vertexai":
        return VertexAIAdapter(**kwargs)

    if et == "native":
        return NativeEngine()

    raise ValueError(f"Unknown engine_type: {engine_type}")


class EngineFactory:
    """
    Engine Factory: Auto-select by Actor Config

    Auto-detect rules:
      - All actors with llm_config=None -> NativeEngine
      - Any actor with llm_config set   -> CrewAIAdapter
      - Mixed actors                    -> CrewAIAdapter (needs LLM for planning)

    Override:
      - engine_type="native"   -> NativeEngine
      - engine_type="crewai"   -> CrewAIAdapter
      - engine_type="vertexai" -> VertexAIAdapter (compatibility)
    """

    @staticmethod
    def create(
        actors: List[Actor],
        engine_type: Optional[str] = None,
        **kwargs,
    ):
        # Fail fast if actors list is empty
        if not actors:
            raise ValueError(
                "EngineFactory.create() requires at least one actor (actors=[] is invalid)"
            )

        # Forced selection
        if engine_type is not None:
            logger.info("EngineFactory forced selection: engine_type=%s", engine_type)
            return create_engine(engine_type, **kwargs)

        # Auto-detect based on actor.llm_config
        any_llm = any(getattr(a, "llm_config", None) is not None for a in actors)

        if any_llm:
            logger.info(
                "EngineFactory selected CrewAIAdapter (reason: at least one actor has llm_config set; LLM needed for planning)"
            )
            return create_engine("crewai", **kwargs)

        logger.info(
            "EngineFactory selected NativeEngine (reason: all actors have llm_config=None; deterministic execution)"
        )
        return create_engine("native", **kwargs)
