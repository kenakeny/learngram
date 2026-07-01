"""Shared text helpers for the ingestion pipeline.

Centralizes logic that was duplicated across the source scrapers and the
extract/embed jobs: topic detection, Markdown H2 splitting, and chunking.
"""
import re

# Keyword → topic map (superset of what primer.py and blogs.py used).
_TOPIC_KEYS: list[tuple[str, list[str]]] = [
    ("networking",          ["load balancer", "proxy", "cdn", "dns", "api gateway", "tcp", "http", "network"]),
    ("caching",             ["cache", "redis", "memcached", "eviction", "bloom filter"]),
    ("databases",           ["database", "sql", "nosql", "sharding", "replication", "index", "b-tree", "storage"]),
    ("distributed-systems", ["distributed", "cap theorem", "cap", "consistent hashing", "consensus",
                             "raft", "paxos", "fault tolerance", "scalab"]),
    ("consistency",         ["acid", "base", "eventual consistency", "strong consistency", "idempotent",
                             "consistency", "eventual", "transaction"]),
    ("messaging",           ["queue", "kafka", "pub/sub", "message broker", "backpressure", "stream", "message"]),
]


def detect_topics(text: str, default: list[str] | None = None) -> list[str]:
    """Return the topics whose keywords appear in `text`.

    `default` is returned when nothing matches (primer wanted
    ['distributed-systems']; blogs wanted [] to drop off-topic posts).
    """
    lower = text.lower()
    hits = [topic for topic, kws in _TOPIC_KEYS if any(k in lower for k in kws)]
    return hits or (default or [])


def slug_anchor(heading: str) -> str:
    """GitHub-style anchor slug for a heading."""
    return re.sub(r"[^a-z0-9\s-]", "", heading.lower()).strip().replace(" ", "-")


def split_markdown_by_h2(content: str, min_body: int = 200) -> list[dict]:
    """Split Markdown into H2 sections.

    Returns [{heading, body, anchor}] for each `## ` section, skipping nav/TOC
    headings and sections with almost no prose. Returns [] when nothing qualifies
    (caller decides on a whole-document fallback).
    """
    skip_headings = {"table of contents", "contributing", "license", "credits"}
    sections: list[dict] = []
    for part in re.split(r"(?m)^(?=## )", content):
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        heading = lines[0].lstrip("# ").strip()
        body = "\n".join(lines[1:]).strip()
        if len(body) < min_body or heading.lower() in skip_headings:
            continue
        sections.append({"heading": heading, "body": body, "anchor": slug_anchor(heading)})
    return sections


def chunk(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    """Split text into overlapping character windows (skips empty windows)."""
    chunks, start = [], 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if piece:
            chunks.append(piece)
        start += size - overlap
    return chunks
