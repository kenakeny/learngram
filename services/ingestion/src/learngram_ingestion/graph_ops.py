"""Non-interactive graph mutations shared by the review CLI and the auto pipeline.

These promote pending `proposals` into real `nodes`/`edges`. The review CLI calls
`approve_node`/`approve_edge` per user keystroke; the ingest pipeline calls
`auto_approve_document` to promote every pending proposal for a document at once.
"""
import uuid
from datetime import datetime, timezone

import psycopg


def _mark_approved(conn: psycopg.Connection, proposal_id: uuid.UUID) -> None:
    conn.execute(
        "UPDATE proposals SET status='approved', reviewed_at=%s WHERE id=%s",
        (datetime.now(timezone.utc), proposal_id),
    )


def approve_node(conn: psycopg.Connection, proposal_id: uuid.UUID, payload: dict,
                 doc_id: uuid.UUID | None) -> uuid.UUID | None:
    """Insert a proposed node and mark the proposal approved.

    Returns the new node id, or None if the slug already existed (still approved).
    """
    row = conn.execute(
        """
        INSERT INTO nodes (name, slug, short_description, topic, depth_level)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
        """,
        (payload["name"], payload["slug"], payload["short_description"],
         payload["topic"], int(payload["depth_level"])),
    ).fetchone()

    node_id = row[0] if row else None
    if node_id and doc_id:
        conn.execute(
            "INSERT INTO source_links (node_id, document_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (node_id, doc_id),
        )

    _mark_approved(conn, proposal_id)
    conn.commit()
    return node_id


def approve_edge(conn: psycopg.Connection, proposal_id: uuid.UUID, payload: dict) -> bool:
    """Insert a proposed edge if both endpoints exist. Returns True on insert.

    When an endpoint node is missing the proposal is left pending (not approved),
    so it can resolve once the missing node is added.
    """
    from_id = conn.execute("SELECT id FROM nodes WHERE slug=%s", (payload["from_slug"],)).fetchone()
    to_id   = conn.execute("SELECT id FROM nodes WHERE slug=%s", (payload["to_slug"],)).fetchone()
    if not from_id or not to_id:
        return False

    conn.execute(
        """
        INSERT INTO edges (from_node_id, to_node_id, relationship_type, weight)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (from_id[0], to_id[0], payload["relationship_type"], float(payload.get("weight", 1.0))),
    )
    _mark_approved(conn, proposal_id)
    conn.commit()
    return True


def auto_approve_document(conn: psycopg.Connection, doc_id: uuid.UUID) -> tuple[int, int]:
    """Promote all pending proposals for a document. Nodes first, then edges.

    Returns (new_nodes, new_edges).
    """
    node_props = conn.execute(
        "SELECT id, payload FROM proposals "
        "WHERE document_id=%s AND kind='node' AND status='pending' ORDER BY created_at",
        (doc_id,),
    ).fetchall()
    new_nodes = sum(
        1 for pid, payload in node_props
        if approve_node(conn, pid, payload, doc_id) is not None
    )

    edge_props = conn.execute(
        "SELECT id, payload FROM proposals "
        "WHERE document_id=%s AND kind='edge' AND status='pending' ORDER BY created_at",
        (doc_id,),
    ).fetchall()
    new_edges = sum(1 for pid, payload in edge_props if approve_edge(conn, pid, payload))

    return new_nodes, new_edges
