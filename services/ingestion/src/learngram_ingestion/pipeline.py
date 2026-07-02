"""Full auto pipeline: documents → concepts → graph → embeddings → cards.

Given document ids that were just inserted (by ingest_file), this runs every
downstream step with NO human review, so a single "ingest" action turns a file
into feed cards. Both the CLI (`ingest-file`) and the API `/ingest` endpoint call
`run_pipeline`; the optional `progress(step, message)` callback lets the API
stream status into the ingest_jobs row while the CLI just prints.
"""
from learngram_shared.config import settings
from learngram_shared.embeddings.factory import get_embeddings
from learngram_shared.llm.factory import get_llm

from .embed import chunk_documents, embed_chunks, embed_nodes
from .extract import load_existing_topics, process_document
from .generate import RateLimiter
from .graph_ops import auto_approve_document
from .personas import generate_posts_for_nodes, load_personas


def _noop(step: str, message: str) -> None:
    pass


def run_pipeline(conn, doc_ids: list, progress=None) -> dict:
    """Extract → auto-approve → embed → generate for the given documents.

    Returns {nodes_added, edges_added, cards_added}. Uses one caller-provided
    connection so it can run inside a CLI process or an API background task.
    """
    progress = progress or _noop
    llm = get_llm()
    embeddings = get_embeddings()
    limiter = RateLimiter(settings.llm_rpm)

    # 1. Extract concepts from each document and promote them into the graph.
    nodes_added = edges_added = 0
    for doc_id in doc_ids:
        row = conn.execute(
            "SELECT title, cleaned_text FROM documents WHERE id = %s", (doc_id,)
        ).fetchone()
        if not row or not row[1]:
            continue
        title, text = row

        existing = [
            {"slug": r[0], "name": r[1]}
            for r in conn.execute("SELECT slug, name FROM nodes ORDER BY name").fetchall()
        ]
        existing_topics = load_existing_topics(conn)
        progress("extract", f"reading {title[:50]}")
        process_document(conn, doc_id, title, text, existing, llm, existing_topics)

        progress("approve", f"building graph from {title[:50]}")
        n, e = auto_approve_document(conn, doc_id)
        nodes_added += n
        edges_added += e

        # Mark processed so an interrupted run can resume where it left off
        # (even when the document yielded zero proposals).
        conn.execute("UPDATE documents SET processed_at = NOW() WHERE id = %s", (doc_id,))
        conn.commit()

    # 2. Embed new nodes + chunk/embed the new documents (needed for RAG grounding).
    progress("embed", "embedding concepts and sources")
    embed_nodes(conn, embeddings, batch=16)
    chunk_documents(conn, rechunk=False)
    embed_chunks(conn, embeddings, batch=16)

    # 3. One post per persona for the concepts this ingest introduced (no posts yet).
    new_nodes = conn.execute(
        """
        SELECT DISTINCT n.id, n.name, n.slug, n.topic, n.depth_level, n.short_description
        FROM nodes n
        JOIN source_links sl ON sl.node_id = n.id
        WHERE sl.document_id = ANY(%s::uuid[])
          AND NOT EXISTS (
              SELECT 1 FROM cards c WHERE c.node_id = n.id AND c.persona_id IS NOT NULL
          )
        """,
        ([str(d) for d in doc_ids],),
    ).fetchall()

    cards_added = 0
    if new_nodes:
        personas = load_personas(conn)
        progress("generate", f"writing persona posts for {len(new_nodes)} concept(s)")
        cards_added = generate_posts_for_nodes(conn, new_nodes, personas, llm, embeddings, limiter, progress)

    return {"nodes_added": nodes_added, "edges_added": edges_added, "cards_added": cards_added}
