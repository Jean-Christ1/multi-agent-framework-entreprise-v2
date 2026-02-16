from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

from framework.types import LLMTelemetry


@dataclass(frozen=True)
class TokenUsage:
    """
    Normalized token usage returned by an LLM provider.
    """

    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class TelemetryCalculator:
    """
    Central telemetry helper used by all engines.

    Responsibilities:
    - measure latency
    - compute LLM cost
    - build LLMTelemetry objects

    This class is engine-agnostic.
    """

    # ####  Spike pricing (example values, configurable later)
    PRICE_PER_1K_TOKENS_USD: Dict[str, float] = {
        "gpt-4o-mini": 0.00015,
        "gpt-4o": 0.00500,
    }

    @staticmethod
    def now_ms() -> int:
        """Return current time in milliseconds."""
        return int(time.time() * 1000)

    @classmethod
    def compute_cost_usd(cls, model: str, total_tokens: int) -> float:
        """
        Compute LLM call cost using a simple per-1k-tokens pricing map.
        """
        price_per_1k = cls.PRICE_PER_1K_TOKENS_USD.get(model, 0.0)
        return (total_tokens / 1000.0) * price_per_1k

    @classmethod
    def build(
        cls,
        *,
        process_id: UUID,
        actor_name: str,
        engine: str,
        model: str,
        usage: TokenUsage,
        latency_ms: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMTelemetry:
        """
        Build a fully-populated LLMTelemetry object.
        """
        total = usage.total_tokens

        return LLMTelemetry(
            process_id=process_id,
            actor_name=actor_name,
            engine=engine,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=total,
            latency_ms=latency_ms,
            cost_usd=cls.compute_cost_usd(model=model, total_tokens=total),
            metadata=metadata or {},
        )
