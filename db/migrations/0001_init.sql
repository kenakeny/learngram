CREATE EXTENSION IF NOT EXISTS vector;

-- Enums
CREATE TYPE relationship_type AS ENUM (
    'prerequisite_of',
    'alternative_to',
    'used_in',
    'example_of',
    'trades_off_with',
    'related_to',
    'evolved_from'
);

CREATE TYPE source_type AS ENUM (
    'primer',
    'blog',
    'arxiv',
    'youtube',
    'wikipedia',
    'hackernews'
);

CREATE TYPE card_format AS ENUM (
    'pattern',
    'war_story',
    'tradeoff',
    'comparison',
    'quiz'
);

-- Knowledge graph nodes
CREATE TABLE nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    short_description TEXT NOT NULL,
    embedding       vector(768),
    topic           TEXT NOT NULL CHECK (topic IN (
                        'networking', 'caching', 'databases',
                        'distributed-systems', 'consistency', 'messaging'
                    )),
    depth_level     SMALLINT NOT NULL CHECK (depth_level BETWEEN 1 AND 5),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Directed edges between nodes
CREATE TABLE edges (
    from_node_id    UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    to_node_id      UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relationship_type relationship_type NOT NULL,
    weight          REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (from_node_id, to_node_id, relationship_type)
);

-- Source documents
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url      TEXT NOT NULL,
    source_type     source_type NOT NULL,
    title           TEXT NOT NULL,
    raw_text        TEXT,
    cleaned_text    TEXT,
    topic_tags      TEXT[] NOT NULL DEFAULT '{}',
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Links from nodes to supporting documents
CREATE TABLE source_links (
    node_id         UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    relevance_score REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (node_id, document_id)
);

-- Generated cards (one or more per node)
CREATE TABLE cards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id         UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    hook            TEXT NOT NULL,
    body            TEXT NOT NULL,
    format          card_format NOT NULL,
    source_doc_ids  UUID[] NOT NULL DEFAULT '{}',
    quality_score   REAL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User interaction events for feed ranking
CREATE TABLE interactions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id     UUID REFERENCES cards(id) ON DELETE SET NULL,
    node_id     UUID REFERENCES nodes(id) ON DELETE SET NULL,
    event_type  TEXT NOT NULL CHECK (event_type IN (
                    'view', 'linger', 'save', 'not_interested', 'go_deeper'
                )),
    linger_ms   INT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_nodes_topic        ON nodes(topic);
CREATE INDEX idx_edges_from         ON edges(from_node_id);
CREATE INDEX idx_edges_to           ON edges(to_node_id);
CREATE INDEX idx_interactions_node  ON interactions(node_id);
CREATE INDEX idx_cards_node         ON cards(node_id);

-- HNSW vector index (harmless over NULLs until Phase 3 backfill)
CREATE INDEX idx_nodes_embedding ON nodes USING hnsw (embedding vector_cosine_ops);
