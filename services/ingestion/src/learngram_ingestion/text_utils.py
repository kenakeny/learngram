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


# Section headings that never contain teachable content: site nav, book
# boilerplate (every textbook chapter ends with Exercises/Summary/Discussion),
# and reference lists. Compared lowercase against the full heading.
_SKIP_HEADINGS = {
    "table of contents", "contributing", "license", "credits",
    "exercises", "exercise", "summary", "discussion", "discussions",
    "references", "further reading", "acknowledgments", "acknowledgements",
    "notation", "changelog", "about the author", "about the authors",
}

_CODE_FENCE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)


def _looks_like_heading(heading: str) -> bool:
    """Reject pseudo-headings: code fences, long sentences, markdown junk.

    The preamble before a file's first H2 gets its first line treated as a
    heading, so this sees arbitrary text (we've stored documents literally
    titled '```{.python .input}').
    """
    return (
        0 < len(heading) <= 80
        and "```" not in heading
        and "`" not in heading
        and not heading.startswith(("{", "[", "<", "|"))
    )


def split_markdown_by_h2(content: str, min_body: int = 200) -> list[dict]:
    """Split Markdown into H2 sections.

    Returns [{heading, body, anchor}] for each `## ` section, skipping nav/TOC
    and boilerplate headings, pseudo-headings, and sections that are mostly
    code or have almost no prose. Returns [] when nothing qualifies (caller
    decides on a whole-document fallback).
    """
    sections: list[dict] = []
    for part in re.split(r"(?m)^(?=## )", content):
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        heading = lines[0].lstrip("# ").strip()
        body = "\n".join(lines[1:]).strip()
        # Prose length is measured with code blocks removed — a section that is
        # one paragraph and three screens of code is not grounding material.
        prose = _CODE_FENCE.sub("", body)
        if (
            len(prose) < min_body
            or heading.lower() in _SKIP_HEADINGS
            or not _looks_like_heading(heading)
        ):
            continue
        sections.append({"heading": heading, "body": body, "anchor": slug_anchor(heading)})
    return sections


# Lines that are calls-to-action, not content. Scraped blogs embed these in the
# article body and they were ending up inside RAG grounding chunks.
_BOILERPLATE_LINE = re.compile(
    r"subscribe|sign\s?up|newsletter|follow (me|us) on|join .{0,40}(discord|slack|community)"
    r"|share this (post|article)|leave a comment|hit the like",
    re.IGNORECASE,
)


def strip_boilerplate(text: str) -> str:
    """Drop CTA/self-promo lines from scraped article text."""
    return "\n".join(
        line for line in text.splitlines() if not _BOILERPLATE_LINE.search(line)
    )


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def chunk(text: str, size: int = 1600, overlap: int = 200) -> list[str]:
    """Split text into ~`size`-char pieces on paragraph/sentence boundaries.

    Never cuts mid-word (the old character-window version produced chunks
    starting with fragments like "nsistent hashing"). `overlap` carries the
    trailing units of one chunk into the next so context isn't lost at seams.
    """
    # Break into units: paragraphs, or sentences when a paragraph is too long.
    # Only something with no sentence structure (e.g. a giant code block) ever
    # falls back to a hard slice.
    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= size:
            units.append(para)
            continue
        for sent in _SENTENCE_END.split(para):
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) <= size:
                units.append(sent)
            else:
                units.extend(
                    p for i in range(0, len(sent), size) if (p := sent[i:i + size].strip())
                )

    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for unit in units:
        if cur and cur_len + len(unit) > size:
            chunks.append("\n\n".join(cur))
            # Carry trailing units (up to `overlap` chars) into the next chunk.
            carry: list[str] = []
            carry_len = 0
            for prev in reversed(cur):
                if carry_len + len(prev) > overlap:
                    break
                carry.insert(0, prev)
                carry_len += len(prev)
            if carry_len + len(unit) > size:
                # No room for both overlap and the new unit — drop the overlap
                # rather than emit a chunk that only duplicates the previous tail.
                carry, carry_len = [], 0
            cur, cur_len = carry, carry_len
        cur.append(unit)
        cur_len += len(unit) + 2
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks
