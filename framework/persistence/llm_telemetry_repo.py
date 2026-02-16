from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from framework.types import LLMTelemetry


class LLMTelemetryRepository:
    """
    Repository responsible for persisting LLM telemetry records.

    Spike scope:
    - write-only access
    - no reads, no aggregation
    - no engine-specific logic
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, telemetry: LLMTelemetry) -> None:
        query = text(
            """
            INSERT INTO llm_telemetry (
                process_id,
                actor_name,
                engine,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                latency_ms,
                cost_usd,
                metadata,
                created_at
            )
            VALUES (
                :process_id,
                :actor_name,
                :engine,
                :model,
                :prompt_tokens,
                :completion_tokens,
                :total_tokens,
                :latency_ms,
                :cost_usd,
                :metadata,
                :created_at
            )
        """
        )

        await self.session.execute(
            query,
            {
                "process_id": str(telemetry.process_id),
                "actor_name": telemetry.actor_name,
                "engine": telemetry.engine,
                "model": telemetry.model,
                "prompt_tokens": telemetry.prompt_tokens,
                "completion_tokens": telemetry.completion_tokens,
                "total_tokens": telemetry.total_tokens,
                "latency_ms": telemetry.latency_ms,
                "cost_usd": telemetry.cost_usd,
                "metadata": json.dumps(telemetry.metadata or {}),
                "created_at": telemetry.created_at,
            },
        )

        await self.session.commit()
