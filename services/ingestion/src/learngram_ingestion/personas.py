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

from .generate import MIN_QUALITY, RateLimiter, _truncate, judge_faithfulness
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
    # The joke is a wrong answer, so the correction ships in the SAME post —
    # the feed never shows uncorrected misinformation.
    "meme": (
        "`headline` = a meme caption starting like \"i asked ChatGPT what <concept> is and it said:\". "
        "`wrong_answer` = the punchline — over-confident, subtly wrong, or obviously copy-pasted. "
        "`correction` = ONE deadpan sentence giving the actually-correct answer. "
        "The correction is shown right under the joke, so it must be genuinely accurate."
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
{json_template}
"""

# The JSON template must name exactly the fields the style's schema requires,
# or small models emit the wrong keys and the post is dropped.
_JSON_TEMPLATES = {
    "meme": '{"headline": "...", "wrong_answer": "...", "correction": "..."}',
    "default": '{"headline": "...", "body": "..."}',
}


def load_personas(conn: psycopg.Connection) -> list[dict]:
    return [
        {"id": r[0], "slug": r[1], "display_name": r[2], "voice": r[3], "post_style": r[4]}
        for r in conn.execute(
            "SELECT id, slug, display_name, voice, post_style FROM personas ORDER BY slug"
        ).fetchall()
    ]


def _grounding_str(grounding: list[dict]) -> str:
    # Full chunk text — callers skip nodes with no grounding, so no fallback.
    return "\n".join(f'  - "{_truncate(g["content"], 1800)}"' for g in grounding)


def generate_post(persona: dict, node: dict, grounding: list[dict], llm, limiter: RateLimiter) -> dict | None:
    """One post in the persona's voice. Returns {hook, body, judged} or None.

    `judged` is the text the faithfulness judge must verify: for the meme
    style that's only the correction (the wrong answer is wrong on purpose);
    for every other style it's the whole post.
    """
    style = persona["post_style"] if persona["post_style"] in STYLE_RULES else "rant"
    prompt = PROMPT.format(
        voice=persona["voice"],
        name=node["name"],
        desc=node["short_description"],
        topic=node["topic"],
        grounding=_grounding_str(grounding),
        style=STYLE_RULES[style],
        json_template=_JSON_TEMPLATES.get(style, _JSON_TEMPLATES["default"]),
    )
    if style == "meme":
        fields = {"headline", "wrong_answer", "correction"}
    else:
        fields = {"headline", "body"}
    schema = {
        "type": "object",
        "properties": {f: {"type": "string"} for f in fields},
        "required": sorted(fields - {"body"}),
    }
    limiter.wait()
    try:
        result = llm.generate(prompt, schema=schema)
        if not isinstance(result, dict):
            result = json.loads(result)
    except Exception as e:
        print(f"LLM error: {e}")
        return None

    # Small models drift on key spelling ("wrong-answer" for "wrong_answer");
    # normalize before reading fields.
    result = {str(k).strip().lower().replace("-", "_"): v for k, v in result.items()}

    headline = str(result.get("headline", "")).strip()
    if not headline:
        return None

    if style == "meme":
        wrong = str(result.get("wrong_answer", "")).strip()
        correction = str(result.get("correction", "")).strip()
        if not wrong or not correction:
            return None
        body = f"{wrong}\n\nthe actual answer: {correction}"
        judged = correction
    else:
        body = str(result.get("body", "")).strip()
        judged = f"{headline}\n{body}".strip()

    return {"hook": _truncate(headline, 200), "body": body, "judged": judged}


def generate_posts_for_nodes(conn, nodes, personas, llm, embeddings, limiter, progress=None) -> int:
    """For each node x persona, generate one grounded in-character post. Returns count."""
    made = 0
    total = len(nodes) * len(personas)
    i = 0
    for row in nodes:
        node_id, name, slug, topic, _depth, desc = row
        node = {"id": node_id, "name": name, "slug": slug, "topic": topic, "short_description": desc}

        # No grounding → no posts for this node (same policy as generate.py).
        grounding = retrieve_grounding(conn, embeddings, node)
        if not grounding:
            i += len(personas)
            print(f"  {name[:30]} — no grounding retrieved, skipping")
            continue
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

            quality, issue = judge_faithfulness(post["judged"], grounding, llm, limiter)
            if quality < MIN_QUALITY:
                print(f"rejected (faithfulness {quality:.1f}: {issue or 'below threshold'})")
                continue

            cur = conn.execute(
                """
                INSERT INTO cards (node_id, persona_id, hook, body, format, post_style, source_doc_ids, quality_score)
                VALUES (%s, %s, %s, %s, 'pattern'::card_format, %s, %s::uuid[], %s)
                """,
                (node_id, p["id"], post["hook"], post["body"], p["post_style"], source_ids, quality),
            )
            made += cur.rowcount
            conn.commit()
            print(f"ok ({quality:.1f})")
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
