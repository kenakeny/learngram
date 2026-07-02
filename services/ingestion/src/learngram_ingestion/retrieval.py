"""RAG retrieval — find the source-document chunks that ground a node's card.

Given a node, embed a short query (name + description) and pull the nearest
`document_chunks` by cosine distance. These chunks become the concrete facts
the card generator must not contradict, and their document ids are recorded on
the card as provenance.
"""
from learngram_shared.vectors import to_pgvector

# Cosine distance ranges 0 (identical) .. 2 (opposite). Chunks beyond this are
# too loosely related to be trustworthy grounding, so we drop them.
#
# Calibrated empirically (2026-07, nomic-embed-text WITH search_query/
# search_document prefixes, 120 sampled nodes): the 4th-best true match sits at
# p90 = 0.304 while a random chunk sits at p10 = 0.371 — 0.34 falls in the gap.
# Recalibrate if the embedding model or prefixing changes: measure top-4 vs
# random-chunk distances and pick a value between the two distributions.
MAX_DISTANCE = 0.34


def retrieve_grounding(conn, embeddings, node: dict, k: int = 4,
                       max_distance: float = MAX_DISTANCE) -> list[dict]:
    """Return up to `k` grounding chunks for a node, nearest first.

    Each item: {content, document_id, title, source_url, distance}.
    Returns [] when nothing relevant is indexed (e.g. no documents ingested yet).
    """
    query = f"{node['name']}. {node['short_description']}"
    qvec = to_pgvector(embeddings.embed([query], task="query")[0])

    rows = conn.execute(
        """
        SELECT dc.content, d.id, d.title, d.source_url,
               dc.embedding <=> %s::vector AS distance
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.embedding IS NOT NULL
        ORDER BY dc.embedding <=> %s::vector
        LIMIT %s
        """,
        (qvec, qvec, k),
    ).fetchall()

    return [
        {
            "content": r[0],
            "document_id": r[1],
            "title": r[2],
            "source_url": r[3],
            "distance": float(r[4]),
        }
        for r in rows
        if float(r[4]) <= max_distance
    ]
