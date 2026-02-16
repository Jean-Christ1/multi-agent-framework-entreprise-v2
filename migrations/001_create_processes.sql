CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE process_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed'
);

CREATE TABLE processes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    status process_status NOT NULL DEFAULT 'pending',

    current_plan JSONB NOT NULL,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_processes_status ON processes(status);
CREATE INDEX idx_processes_updated_at ON processes(updated_at DESC);
