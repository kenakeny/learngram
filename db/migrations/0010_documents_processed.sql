-- Track which documents the extraction pipeline has actually processed, so an
-- interrupted ingest can resume. "Has proposals" is not a reliable marker —
-- some documents legitimately yield zero proposals and would be re-picked forever.
ALTER TABLE documents ADD COLUMN processed_at TIMESTAMPTZ;

-- Backfill: anything that already produced proposals was processed.
UPDATE documents d SET processed_at = NOW()
WHERE EXISTS (SELECT 1 FROM proposals p WHERE p.document_id = d.id);
