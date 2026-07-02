"""
Persona posts — each concept gets one post from every persona "account", each in
that persona's voice and signature format (see the `personas` table).

Usage:
  uv run generate-posts              # for nodes without persona posts yet
  uv run generate-posts --limit 5    # cap number of nodes
  uv run generate-posts --regen      # also (re)generate for nodes that have posts
"""
import json
import sys

import psycopg

from learngram_shared.config import settings
from learngram_shared.embeddings.factory import get_embeddings
from learngram_shared.llm.factory import get_llm

from .generate import RateLimiter, _truncate
from .retrieval import retrieve_grounding

# Per-style formatting rules. `headline` -> cards.hook, `body` -> cards.body.
STYLE_RULES = {
    "oneliner": (
        "Write exactly ONE confident sentence — the whole post. "
        "`headline` = that single sentence. `body` = \"\" (empty)."
    ),
    "rant": (
        "`headline` = a short punchy opener (max ~90 chars). "
        "`body` = a weary 2-4 sentence rant that still teaches the idea."
    ),
    "stackoverflow": (
        "`headline` = the question, phrased like a StackOverflow title "
        "(e.g. \"How does X actually work?\"). "
        "`body` = your clear step-by-step answer with one concrete example."
    ),
    "meme": (
        "`headline` = a meme caption starting like \"i asked ChatGPT what <concept> is and it said:\". "
        "`body` = the punchline — over-confident, subtly wrong, or obviously copy-pasted."
    ),
}

PROMPT = """{voice}

You are posting on a developer social feed. Stay fully in character as described above.

Concept you are posting about: {name}
What it is: {desc}
Topic: {topic}

Source facts (retrieved from real docs — stay consistent with these; you may pull a concrete detail):
{grounding}

Task: write ONE post about this concept, in your voice and your signature format.
Format rules for THIS post:
{style}

Keep it feed-sized. Do not break character. Respond with ONLY a JSON object:
{{"headline": "...", "body": "..."}}
"""


def load_personas(conn: psycopg.Connection) -> list[dict]:
    return [
        {"id": r[0], "slug": r[1], "display_name": r[2], "voice": r[3], "post_style": r[4]}
        for r in conn.execute(
            "SELECT id, slug, display_name, voice, post_style FROM personas ORDER BY slug"
        ).fetchall()
    ]


def _grounding_str(grounding: list[dict]) -> str:
    if not grounding:
        return "  (no specific source facts — rely on the concept description and stay accurate)"
    return "\n".join(f'  - "{_truncate(g["content"], 300)}"' for g in grounding)


def generate_post(persona: dict, node: dict, grounding: list[dict], llm, limiter: RateLimiter) -> dict | None:
    prompt = PROMPT.format(
        voice=persona["voice"],
        name=node["name"],
        desc=node["short_description"],
        topic=node["topic"],
        grounding=_grounding_str(grounding),
        style=STYLE_RULES.get(persona["post_style"], STYLE_RULES["rant"]),
    )
    schema = {
        "type": "object",
        "properties": {"headline": {"type": "string"}, "body": {"type": "string"}},
        "required": ["headline"],
    }
    limiter.wait()
    try:
        result = llm.generate(prompt, schema=schema)
        if not isinstance(result, dict):
            result = json.loads(result)
    except Exception as e:
        print(f"LLM error: {e}")
        return None

    headline = str(result.get("headline", "")).strip()
    body = str(result.get("body", "")).strip()
    if not headline:
        return None
    return {"hook": _truncate(headline, 200), "body": body}


def generate_posts_for_nodes(conn, nodes, personas, llm, embeddings, limiter, progress=None) -> int:
    """For each node x persona, generate one grounded in-character post. Returns count."""
    made = 0
    total = len(nodes) * len(personas)
    i = 0
    for row in nodes:
        node_id, name, slug, topic, _depth, desc = row
        node = {"id": node_id, "name": name, "slug": slug, "topic": topic, "short_description": desc}

        grounding = retrieve_grounding(conn, embeddings, node)
        source_ids = list({str(g["document_id"]) for g in grounding})

        for p in personas:
            i += 1
            print(f"  {name[:30]} · @{p['slug']}", end=" … ", flush=True)
            if progress:
                progress("posts", f"{i}/{total} · @{p['slug']} on {name[:28]}")
            post = generate_post(p, node, grounding, llm, limiter)
            if not post:
                print("failed")
                continue
            cur = conn.execute(
                """
                INSERT INTO cards (node_id, persona_id, hook, body, format, post_style, source_doc_ids, quality_score)
                VALUES (%s, %s, %s, %s, 'pattern'::card_format, %s, %s::uuid[], 0.5)
                """,
                (node_id, p["id"], post["hook"], post["body"], p["post_style"], source_ids),
            )
            made += cur.rowcount
            conn.commit()
            print("ok")
    return made


def main() -> None:
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 25
    regen = "--regen" in args

    llm = get_llm()
    embeddings = get_embeddings()
    limiter = RateLimiter(settings.llm_rpm)

    with psycopg.connect(settings.database_url) as conn:
        personas = load_personas(conn)
        if not personas:
            print("No personas found. Run `uv run migrate` first.")
            return

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
                WHERE NOT EXISTS (
                    SELECT 1 FROM cards c WHERE c.node_id = n.id AND c.persona_id IS NOT NULL
                )
                LIMIT %s
                """,
                (limit,),
            ).fetchall()

        if not nodes:
            print("All nodes already have persona posts. Use --regen to add more.")
            return

        print(f"Generating persona posts: {len(nodes)} node(s) x {len(personas)} personas "
              f"= {len(nodes) * len(personas)} posts…\n")
        made = generate_posts_for_nodes(conn, nodes, personas, llm, embeddings, limiter)

    print(f"\nDone. {made} persona posts created. Refresh the feed.")
