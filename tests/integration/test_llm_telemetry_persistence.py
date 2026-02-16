import pytest
from uuid import uuid4
from sqlalchemy import text

from framework.observability.telemetry import TelemetryCalculator, TokenUsage
from framework.persistence.llm_telemetry_repo import LLMTelemetryRepository


@pytest.mark.asyncio
async def test_llm_telemetry_is_persisted(async_session):
    repo = LLMTelemetryRepository(async_session)

    telemetry = TelemetryCalculator.build(
        process_id=uuid4(),
        actor_name="ProvisionningActor",
        engine="crewai",
        model="gpt-4o-mini",
        usage=TokenUsage(prompt_tokens=123, completion_tokens=77),
        latency_ms=1400,
        metadata={"test": "llm-telemetry"},
    )

    await repo.save(telemetry)

    result = await async_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM llm_telemetry
            WHERE process_id = :process_id
        """
        ),
        {"process_id": str(telemetry.process_id)},
    )

    assert result.scalar_one() == 1
