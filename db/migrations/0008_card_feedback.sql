-- Human feedback on generated cards. Powers the RLHF-style tuning loop that
-- evolves the analogy system prompt (services/ingestion/.../prompts/analogy_system.md).
CREATE TABLE card_feedback (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id    UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    node_id    UUID,
    rating     TEXT        NOT NULL CHECK (rating IN ('up', 'down')),
    comment    TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_card_feedback_card ON card_feedback(card_id);
