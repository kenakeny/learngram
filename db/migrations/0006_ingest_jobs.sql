-- Tracks a one-shot "ingest a file" run so the frontend can poll progress while
-- the API processes it in the background (convert → extract → approve → embed → generate).
CREATE TYPE ingest_status AS ENUM ('pending', 'running', 'done', 'error');

CREATE TABLE ingest_jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename    TEXT          NOT NULL,
    status      ingest_status NOT NULL DEFAULT 'pending',
    step        TEXT          NOT NULL DEFAULT 'queued',
    message     TEXT          NOT NULL DEFAULT '',
    nodes_added INT           NOT NULL DEFAULT 0,
    cards_added INT           NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX idx_ingest_jobs_created ON ingest_jobs(created_at DESC);
