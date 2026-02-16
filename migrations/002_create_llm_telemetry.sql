CREATE TABLE IF NOT EXISTS llm_telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    process_id UUID NOT NULL,
    actor_name TEXT NOT NULL,

    engine TEXT NOT NULL,
    model TEXT NOT NULL,

    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    total_tokens INT NOT NULL,

    latency_ms INT NOT NULL,
    cost_usd NUMERIC(12, 6) NOT NULL,

    metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_telemetry_process_id ON llm_telemetry(process_id);
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_actor_name ON llm_telemetry(actor_name);
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_created_at ON llm_telemetry(created_at DESC);
