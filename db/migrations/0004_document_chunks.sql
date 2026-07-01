-- Chunk-level embeddings for RAG retrieval over source documents.
-- Cards are grounded by retrieving the nearest chunks to a node, so the
-- retrieval unit is a chunk (not a whole document, which would be too coarse).
CREATE TABLE document_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal      INT  NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector(768),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, ordinal)
);

CREATE INDEX idx_document_chunks_doc ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
