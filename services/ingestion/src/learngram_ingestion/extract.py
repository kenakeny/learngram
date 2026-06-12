"""
LLM extraction job — reads unprocessed documents, proposes new nodes/edges.

Usage:  uv run extract [--limit N] [--doc-id UUID]
"""
import json
import re
import sys
import time
import uuid

import psycopg

from learngram_shared.config import settings
from learngram_shared.llm.factory import get_llm

CHUNK_SIZE    = 2000   # chars
CHUNK_OVERLAP = 200
RATE_DELAY    = 0    # seconds between Ollama calls

PROMPT_TEMPLATE = """\
You are building a system-design knowledge graph. Analyze the text below and \
extract concepts that could extend the graph.

Existing nodes (do NOT propose these — use their slugs in edges instead):
{existing_nodes}

Document title: {title}
---
{chunk}
---

Respond with ONLY a valid JSON object. No explanation, no markdown, just JSON.

{{
  "new_nodes_proposed": [
    {{
      "name": "Human-readable name",
      "slug": "kebab-case-unique-slug",
      "short_description": "One factual sentence, max 150 chars.",
      "topic": "<one of: networking|caching|databases|distributed-systems|consistency|messaging>",
      "depth_level": <integer 1-5>
    }}
  ],
  "edges_proposed": [
    {{
      "from_slug": "slug-of-source-node",
      "to_slug": "slug-of-target-node",
      "relationship_type": "<one of: prerequisite_of|alternative_to|used_in|example_of|trades_off_with|related_to|evolved_from>",
      "weight": <float 0.5-1.5>
    }}
  ],
  "existing_nodes_referenced": ["slug1", "slug2"]
}}

Rules:
- Only propose nodes for concepts NOT in the existing list above.
- Edges can connect existing nodes to each other OR to newly proposed nodes.
- depth_level: 1=intro, 2=foundational, 3=intermediate, 4=advanced, 5=specialist.
- If nothing new is found, return empty arrays — do not invent content.
"""

VALID_TOPICS = {"networking", "caching", "databases", "distributed-systems", "consistency", "messaging"}
VALID_REL    = {"prerequisite_of", "alternative_to", "used_in", "example_of", "trades_off_with", "related_to", "evolved_from"}


def _chunk(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return chunks


def _extract_json(raw: str) -> dict:
    """Parse JSON from LLM response, tolerating surrounding text."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to find a JSON object in the response
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def _validate_node(n: dict, existing_slugs: set[str]) -> str | None:
    """Return error string or None if valid."""
    for f in ("name", "slug", "short_description", "topic", "depth_level"):
        if f not in n:
            return f"missing field {f!r}"
    if n["topic"] not in VALID_TOPICS:
        return f"invalid topic {n['topic']!r}"
    if n["slug"] in existing_slugs:
        return f"slug {n['slug']!r} already exists"
    if not re.match(r"^[a-z0-9-]+$", n["slug"]):
        return f"invalid slug {n['slug']!r}"
    if not isinstance(n["depth_level"], int) or not 1 <= n["depth_level"] <= 5:
        return "depth_level must be int 1-5"
    if len(n["short_description"]) > 200:
        return "short_description too long"
    return None


def _validate_edge(e: dict, all_slugs: set[str]) -> str | None:
    for f in ("from_slug", "to_slug", "relationship_type"):
        if f not in e:
            return f"missing field {f!r}"
    if e["relationship_type"] not in VALID_REL:
        return f"invalid relationship_type {e['relationship_type']!r}"
    if e["from_slug"] not in all_slugs:
        return f"unknown from_slug {e['from_slug']!r}"
    if e["to_slug"] not in all_slugs:
        return f"unknown to_slug {e['to_slug']!r}"
    if e["from_slug"] == e["to_slug"]:
        return "self-loop"
    return None


def process_document(conn: psycopg.Connection, doc_id: uuid.UUID, title: str,
                     text: str, existing_nodes: list[dict], llm) -> tuple[int, int]:
    """Extract proposals from one document. Returns (nodes_added, edges_added)."""
    existing_slugs = {n["slug"] for n in existing_nodes}
    node_list_str  = "\n".join(f"  - {n['slug']} ({n['name']})" for n in existing_nodes)

    chunks         = _chunk(text)
    session_slugs  = set(existing_slugs)   # grows as we propose new nodes
    nodes_added = edges_added = 0

    for i, chunk in enumerate(chunks, 1):
        print(f"    chunk {i}/{len(chunks)} …", end=" ", flush=True)
        prompt = PROMPT_TEMPLATE.format(
            existing_nodes=node_list_str,
            title=title,
            chunk=chunk,
        )

        try:
            raw = llm.generate(prompt)
            data = _extract_json(raw if isinstance(raw, str) else json.dumps(raw))
        except Exception as e:
            print(f"LLM/parse error: {e}")
            time.sleep(RATE_DELAY)
            continue

        proposed_nodes = data.get("new_nodes_proposed") or []
        proposed_edges = data.get("edges_proposed") or []

        # Insert node proposals
        new_in_chunk: set[str] = set()
        for node in proposed_nodes:
            err = _validate_node(node, session_slugs | new_in_chunk)
            if err:
                continue
            # Check for duplicate proposal
            dup = conn.execute(
                "SELECT 1 FROM proposals WHERE kind='node' AND payload->>'slug' = %s",
                (node["slug"],),
            ).fetchone()
            if dup:
                new_in_chunk.add(node["slug"])   # might still be referenced in edges
                continue
            conn.execute(
                "INSERT INTO proposals (document_id, kind, payload) VALUES (%s, 'node', %s)",
                (doc_id, json.dumps(node)),
            )
            new_in_chunk.add(node["slug"])
            nodes_added += 1

        session_slugs |= new_in_chunk

        # Insert edge proposals
        for edge in proposed_edges:
            err = _validate_edge(edge, session_slugs)
            if err:
                continue
            dup = conn.execute(
                """SELECT 1 FROM proposals WHERE kind='edge'
                   AND payload->>'from_slug' = %s
                   AND payload->>'to_slug'   = %s
                   AND payload->>'relationship_type' = %s""",
                (edge["from_slug"], edge["to_slug"], edge["relationship_type"]),
            ).fetchone()
            if dup:
                continue
            edge.setdefault("weight", 1.0)
            conn.execute(
                "INSERT INTO proposals (document_id, kind, payload) VALUES (%s, 'edge', %s)",
                (doc_id, json.dumps(edge)),
            )
            edges_added += 1

        conn.commit()
        print(f"{nodes_added}n {edges_added}e so far")
        time.sleep(RATE_DELAY)

    return nodes_added, edges_added


def main() -> None:
    args    = sys.argv[1:]
    limit   = int(args[args.index("--limit") + 1]) if "--limit" in args else 50
    doc_id  = args[args.index("--doc-id") + 1]    if "--doc-id" in args else None

    llm = get_llm()
    print(f"LLM provider: {settings.llm_provider} / model: {settings.ollama_gen_model}")

    with psycopg.connect(settings.database_url) as conn:
        # Load current nodes
        existing_nodes = [
            {"slug": r[0], "name": r[1]}
            for r in conn.execute("SELECT slug, name FROM nodes ORDER BY name").fetchall()
        ]

        # Select documents to process
        if doc_id:
            docs = conn.execute(
                "SELECT id, title, cleaned_text FROM documents WHERE id = %s",
                (doc_id,),
            ).fetchall()
        else:
            docs = conn.execute(
                """
                SELECT d.id, d.title, d.cleaned_text
                FROM documents d
                WHERE d.cleaned_text IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM proposals p WHERE p.document_id = d.id
                  )
                LIMIT %s
                """,
                (limit,),
            ).fetchall()

    if not docs:
        print("No unprocessed documents found. Run ingest-primer or ingest-blogs first.")
        return

    print(f"Processing {len(docs)} document(s) …\n")
    total_n = total_e = 0

    with psycopg.connect(settings.database_url) as conn:
        for doc in docs:
            doc_id_val, title, text = doc
            if not text:
                continue
            print(f"  [{doc_id_val}] {title[:70]}")
            n, e = process_document(conn, doc_id_val, title, text, existing_nodes, llm)
            total_n += n
            total_e += e
            print(f"    → {n} node proposals, {e} edge proposals\n")

    print(f"Extraction complete. Total: {total_n} node proposals, {total_e} edge proposals.")
    print("Run `uv run review` to approve them.")
