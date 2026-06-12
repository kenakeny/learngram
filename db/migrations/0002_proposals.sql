CREATE TYPE proposal_kind   AS ENUM ('node', 'edge');
CREATE TYPE proposal_status AS ENUM ('pending', 'approved', 'rejected');

CREATE TABLE proposals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    kind        proposal_kind   NOT NULL,
    payload     JSONB           NOT NULL,
    status      proposal_status NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX idx_proposals_status ON proposals(status);
CREATE INDEX idx_proposals_doc    ON proposals(document_id);
