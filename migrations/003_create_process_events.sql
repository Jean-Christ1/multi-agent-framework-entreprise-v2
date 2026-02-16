BEGIN;

-- ============================================================================
-- ENUM: process_event_status
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'process_event_status'
    ) THEN
        CREATE TYPE process_event_status AS ENUM ('complete', 'error');
    END IF;
END
$$;

-- ============================================================================
-- TABLE: process_events
-- ============================================================================

CREATE TABLE IF NOT EXISTS process_events (
    id UUID PRIMARY KEY,
    process_id UUID NOT NULL
        REFERENCES processes(id)
        ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(255) NOT NULL,
    message TEXT,
    status process_event_status NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_process_events_process_created
    ON process_events (process_id, created_at);

COMMIT;
