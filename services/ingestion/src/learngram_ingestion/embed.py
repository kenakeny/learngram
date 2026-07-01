"""
Embedding backfill — populate vector embeddings so RAG retrieval works.

Two targets:
  - nodes            : embed name + short_description into nodes.embedding
  - document chunks  : split each document's cleaned_text and embed each chunk

Usage:
  uv run embed                 # embed nodes + chunk/embed documents (missing only)
  uv run embed --nodes         # only nodes
  uv run embed --docs          # only document chunks
  uv run embed --rechunk       # drop existing chunks and rebuild from scratch
  uv run embed --batch 32      # embeddings per LLM call (default 16)
"""
import sys

import psycopg

from learngram_shared.config import settings
from learngram_shared.embeddings.factory import get_embeddings
from learngram_shared.vectors import to_pgvector

CHUNK_SIZE    = 2000   # chars — matches the extraction chunker
CHUNK_OVERLAP = 200


def _chunk(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_SIZE
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end - CHUNK_OVERLAP
    return chunks


def _batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def embed_nodes(conn: psycopg.Connection, embeddings, batch: int) -> int:
    rows = conn.execute(
        "SELECT id, name, short_description FROM nodes WHERE embedding IS NULL"
    ).fetchall()
    if not rows:
        print("  nodes: all embedded")
        return 0

    print(f"  nodes: embedding {len(rows)} …", flush=True)
    done = 0
    for group in _batched(rows, batch):
        texts = [f"{name}. {desc}" for _, name, desc in group]
        vecs = embeddings.embed(texts)
        for (node_id, _, _), vec in zip(group, vecs):
            conn.execute(
                "UPDATE nodes SET embedding = %s::vector WHERE id = %s",
                (to_pgvector(vec), node_id),
            )
        conn.commit()
        done += len(group)
        print(f"    {done}/{len(rows)}", flush=True)
    return done


def chunk_documents(conn: psycopg.Connection, rechunk: bool) -> int:
    """Split documents into `document_chunks` rows (without embeddings yet)."""
    if rechunk:
        conn.execute("TRUNCATE document_chunks")
        conn.commit()
        docs = conn.execute(
            "SELECT id, cleaned_text FROM documents WHERE cleaned_text IS NOT NULL"
        ).fetchall()
    else:
        docs = conn.execute(
            """
            SELECT d.id, d.cleaned_text
            FROM documents d
            WHERE d.cleaned_text IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM document_chunks c WHERE c.document_id = d.id)
            """
        ).fetchall()

    if not docs:
        print("  chunks: documents already chunked")
        return 0

    total = 0
    for doc_id, text in docs:
        for ordinal, piece in enumerate(_chunk(text)):
            conn.execute(
                """
                INSERT INTO document_chunks (document_id, ordinal, content)
                VALUES (%s, %s, %s)
                ON CONFLICT (document_id, ordinal) DO NOTHING
                """,
                (doc_id, ordinal, piece),
            )
            total += 1
        conn.commit()
    print(f"  chunks: created {total} from {len(docs)} document(s)")
    return total


def embed_chunks(conn: psycopg.Connection, embeddings, batch: int) -> int:
    rows = conn.execute(
        "SELECT id, content FROM document_chunks WHERE embedding IS NULL"
    ).fetchall()
    if not rows:
        print("  chunks: all embedded")
        return 0

    print(f"  chunks: embedding {len(rows)} …", flush=True)
    done = 0
    for group in _batched(rows, batch):
        vecs = embeddings.embed([content for _, content in group])
        for (chunk_id, _), vec in zip(group, vecs):
            conn.execute(
                "UPDATE document_chunks SET embedding = %s::vector WHERE id = %s",
                (to_pgvector(vec), chunk_id),
            )
        conn.commit()
        done += len(group)
        print(f"    {done}/{len(rows)}", flush=True)
    return done


def main() -> None:
    args    = sys.argv[1:]
    do_nodes = "--nodes" in args or not ("--docs" in args or "--nodes" in args)
    do_docs  = "--docs" in args or not ("--docs" in args or "--nodes" in args)
    rechunk  = "--rechunk" in args
    batch    = int(args[args.index("--batch") + 1]) if "--batch" in args else 16

    embeddings = get_embeddings()
    provider = settings.embedding_provider
    model = settings.gemini_embed_model if provider == "gemini" else settings.ollama_embed_model
    print(f"Embeddings: {provider} / {model}  (batch {batch})")

    with psycopg.connect(settings.database_url) as conn:
        if do_nodes:
            embed_nodes(conn, embeddings, batch)
        if do_docs:
            chunk_documents(conn, rechunk)
            embed_chunks(conn, embeddings, batch)

    print("\nDone. Retrieval is ready — run `uv run generate` to make grounded cards.")
