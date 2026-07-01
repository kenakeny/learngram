"""
Card generation — one brainrot LLM call per node, fanned out into
pattern / analogy / meme feed cards.

Usage:
  uv run generate              # generate for all nodes without a card
  uv run generate --limit 10   # cap at 10 nodes
  uv run generate --regen      # regenerate even nodes that already have cards
"""
import json
import re
import sys
import time

import psycopg

from learngram_shared.config import settings
from learngram_shared.embeddings.factory import get_embeddings
from learngram_shared.llm.factory import get_llm

from .retrieval import retrieve_grounding

REQUIRED_FIELDS = ("explanation", "analogy", "why_it_works", "takeaway", "meme_caption")


class RateLimiter:
    """Spaces calls to stay under a requests-per-minute ceiling."""

    def __init__(self, rpm: int) -> None:
        self._min_interval = 60.0 / rpm if rpm > 0 else 0.0
        self._last = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last
        sleep_for = self._min_interval - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last = time.monotonic()


def _retry_after_seconds(err: Exception, attempt: int) -> float:
    """Honor a server-provided retry delay if present, else exponential backoff."""
    m = re.search(r"retry.?(?:after|delay)\D*(\d+(?:\.\d+)?)", str(err), re.IGNORECASE)
    if m:
        return float(m.group(1))
    return min(60.0, 2.0**attempt)  # 2, 4, 8, 16, 32, capped at 60s


def _is_rate_limit(err: Exception) -> bool:
    s = str(err).lower()
    return "429" in s or "resource_exhausted" in s or "rate limit" in s or "quota" in s


def generate_with_retry(prompt: str, schema: dict, llm, limiter: RateLimiter) -> str | dict:
    """Call the LLM, respecting the rate limit and retrying on 429/quota errors."""
    for attempt in range(settings.llm_max_retries):
        limiter.wait()
        try:
            return llm.generate(prompt, schema=schema)
        except Exception as e:
            if not _is_rate_limit(e) or attempt == settings.llm_max_retries - 1:
                raise
            backoff = _retry_after_seconds(e, attempt)
            print(f"\n    rate limited — backing off {backoff:.0f}s (attempt {attempt + 1})", flush=True)
            time.sleep(backoff)
    raise RuntimeError("unreachable")

PROMPT_TEMPLATE = """\
You're a chronic twitter/internet brainrot user who also happens to be a \
senior systems engineer. You make system design concepts unforgettable.

Context (retrieved from the knowledge graph):
- Concept: {name}
- What it is: {desc}
- Topic: {topic}
- Related concepts:
{related_str}

Source facts (retrieved from real system-design docs — your explanation MUST be \
consistent with these and should draw a concrete detail from them):
{grounding_str}

Given the context above:
1. Explain it normally in 100 words or less.
2. Create an absurd analogy from a completely different domain \
(cooking, dating, gym culture, MMOs, reality TV — anywhere but computing).
3. Explain why the analogy actually works.
4. Give a memorable one-line takeaway (ONE sentence, max 100 characters).
5. Generate a meme caption (max 140 characters, actual meme format, actually funny).

STYLE RULES — violating any of these means you failed:
- The explanation must stay faithful to the Source facts above. Do not invent \
numbers, product names, or behavior that contradicts them.
- BANNED: "It's all about", "Think of it as", "Plus,", "Perfect for", \
"future-proofing", "drastically improves", "boosting speed", any LinkedIn-speak.
- The meme caption must use a real meme format: "nobody: / X:", \
"me explaining X to Y", "X is just Y with extra steps", greentext, \
"POV:", "X: exists / Y:", lowercase shitpost energy. NOT a product description.
- The takeaway is ONE punchy sentence. Not two. It must fit on one line.
- The analogy opens with a concrete scene, not a definition.

Example of GOOD output (for "Load Balancer"):
{{"explanation": "A load balancer sits in front of your servers and spreads \
incoming requests across them so no single server melts. It health-checks \
backends and stops routing to dead ones.", \
"analogy": "It's the bouncer at a club with five identical dance floors. \
Everyone lines up at one door, and the bouncer points each person to whichever \
floor is emptiest. If floor 3 catches fire, he just stops sending people there.", \
"why_it_works": "The bouncer never dances himself — he only routes. Same with \
the load balancer: it does no business logic, it just distributes and watches health.", \
"takeaway": "one entrance, many rooms, and the bouncer never lies about capacity", \
"meme_caption": "nobody: / my single EC2 instance at 3am during a product launch: \
it's free real estate"}}

Respond with ONLY a valid JSON object — no markdown, no explanation:
{{"explanation": "...", "analogy": "...", "why_it_works": "...", "takeaway": "...", "meme_caption": "..."}}
"""


def _truncate(text: str, limit: int) -> str:
    """Cut at a word boundary, never mid-word."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut + "…"


def build_prompt(node: dict, edges: list[dict], grounding: list[dict]) -> str:
    related = [
        f"  - {e['related_name']} ({e['relationship_type'].replace('_', ' ')})"
        for e in edges[:5]
    ]
    related_str = "\n".join(related) if related else "  (none)"

    if grounding:
        grounding_str = "\n".join(
            f'  - "{_truncate(g["content"], 400)}"  (source: {g["title"]})'
            for g in grounding
        )
    else:
        grounding_str = (
            "  (no source documents retrieved — rely on the concept description "
            "above and general knowledge; stay accurate)"
        )

    return PROMPT_TEMPLATE.format(
        name=node["name"],
        desc=node["short_description"],
        topic=node["topic"],
        related_str=related_str,
        grounding_str=grounding_str,
    )


def generate_parts(node: dict, edges: list[dict], grounding: list[dict],
                   llm, limiter: RateLimiter) -> dict | None:
    """One LLM call → dict with the 5 brainrot parts, or None on failure."""
    prompt = build_prompt(node, edges, grounding)

    try:
        schema = {
            "type": "object",
            "properties": {f: {"type": "string"} for f in REQUIRED_FIELDS},
            "required": list(REQUIRED_FIELDS),
        }
        result = generate_with_retry(prompt, schema, llm, limiter)
        if not isinstance(result, dict):
            result = json.loads(result)
    except Exception as e:
        print(f"LLM error: {e}")
        return None

    parts = {f: str(result.get(f, "")).strip() for f in REQUIRED_FIELDS}
    missing = [f for f in REQUIRED_FIELDS if not parts[f]]
    if missing:
        print(f"missing fields: {', '.join(missing)} — skipping")
        return None
    return parts


def build_cards(parts: dict) -> list[dict]:
    """Fan the 5 parts into up to 3 feed cards."""
    analogy_hook = _truncate(parts["analogy"].split(". ")[0], 140)
    return [
        {"format": "pattern", "hook": _truncate(parts["takeaway"], 140),     "body": parts["explanation"]},
        {"format": "analogy", "hook": analogy_hook,                          "body": f"{parts['analogy']}\n\nWhy it works: {parts['why_it_works']}"},
        {"format": "meme",    "hook": _truncate(parts["meme_caption"], 140), "body": parts["explanation"]},
    ]


def generate_cards_for_nodes(conn, nodes, llm, embeddings, limiter, progress=None) -> tuple[int, int]:
    """Generate RAG-grounded cards for each node row.

    `nodes` is a list of (id, name, slug, topic, depth_level, short_description).
    Returns (nodes_ok, cards_inserted). `progress(step, msg)` is called per node
    when supplied (used by the ingest pipeline to report status).
    """
    ok = cards_added = 0
    total = len(nodes)

    for i, row in enumerate(nodes, 1):
        node_id, name, slug, topic, depth_level, short_description = row
        node = {
            "id": node_id, "name": name, "slug": slug,
            "topic": topic, "depth_level": depth_level,
            "short_description": short_description,
        }

        # Related nodes via edges (both directions) — grounds the analogy
        edges = [
            {"related_name": r[0], "relationship_type": r[1]}
            for r in conn.execute(
                """
                SELECT n2.name, e.relationship_type
                FROM edges e
                JOIN nodes n2 ON n2.id = e.to_node_id
                WHERE e.from_node_id = %s
                UNION
                SELECT n2.name, e.relationship_type
                FROM edges e
                JOIN nodes n2 ON n2.id = e.from_node_id
                WHERE e.to_node_id = %s
                """,
                (node_id, node_id),
            ).fetchall()
        ]

        # RAG: retrieve grounding facts from source docs for this node
        grounding = retrieve_grounding(conn, embeddings, node)
        source_ids = list({str(g["document_id"]) for g in grounding})

        print(f"  {name[:50]} [{len(grounding)} facts]", end=" … ", flush=True)
        if progress:
            progress("generate", f"{i}/{total} · {name[:40]}")

        parts = generate_parts(node, edges, grounding, llm, limiter)
        if parts is None:
            print("failed")
            continue

        for card in build_cards(parts):
            cur = conn.execute(
                """
                INSERT INTO cards (node_id, hook, body, format, source_doc_ids, quality_score)
                VALUES (%s, %s, %s, %s::card_format, %s::uuid[], 0.5)
                ON CONFLICT DO NOTHING
                """,
                (node_id, card["hook"], card["body"], card["format"], source_ids),
            )
            cards_added += cur.rowcount
        conn.commit()
        print(f"ok — {parts['meme_caption'][:55]!r}")
        ok += 1

    return ok, cards_added


def main() -> None:
    args  = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 100
    regen = "--regen" in args

    llm = get_llm()
    embeddings = get_embeddings()
    limiter = RateLimiter(settings.llm_rpm)
    model = settings.gemini_gen_model if settings.llm_provider == "gemini" else settings.ollama_gen_model
    print(f"LLM: {settings.llm_provider} / {model}  ({settings.llm_rpm} rpm)")

    with psycopg.connect(settings.database_url) as conn:
        if regen:
            nodes = conn.execute(
                "SELECT id, name, slug, topic, depth_level, short_description FROM nodes LIMIT %s",
                (limit,),
            ).fetchall()
        else:
            nodes = conn.execute(
                """
                SELECT n.id, n.name, n.slug, n.topic, n.depth_level, n.short_description
                FROM nodes n
                WHERE NOT EXISTS (SELECT 1 FROM cards c WHERE c.node_id = n.id)
                LIMIT %s
                """,
                (limit,),
            ).fetchall()

        if not nodes:
            print("All nodes already have cards. Use --regen to regenerate.")
            return

        print(f"Generating cards for {len(nodes)} node(s)…\n")
        ok, cards = generate_cards_for_nodes(conn, nodes, llm, embeddings, limiter)

    print(f"\nDone. {ok} nodes → {cards} cards.")
    print("Refresh the feed to see them.")
