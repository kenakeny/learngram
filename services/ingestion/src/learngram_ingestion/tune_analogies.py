"""
Tune the analogy voice from human feedback — the RLHF-style loop's tuning step.

Reads recent `card_feedback` joined to `cards` (prioritizing analogies), summarizes
the up-voted vs down-voted examples and comments, asks the LLM to distill a few
CONCRETE, ADDITIVE style lessons grounded in that feedback, then merges them into
the `## Learned preferences` section of prompts/analogy_system.md.

Loop: rate cards in the feed → `uv run tune-analogies` → analogy_system.md grows
→ next `uv run generate` reads the improved voice.

Usage:
  uv run tune-analogies              # distill + write into analogy_system.md
  uv run tune-analogies --limit 200  # cap how many feedback rows to consider
  uv run tune-analogies --dry-run    # print proposed lessons, write nothing
"""
import json
import sys
from pathlib import Path

import psycopg

from learngram_shared.config import settings
from learngram_shared.llm.factory import get_llm

from .generate import _SYSTEM_PROMPT_PATH

LEARNED_HEADER = "## Learned preferences (auto-updated from human feedback)"
_MARKER_COMMENT = "<!-- The tune-analogies job appends distilled"


def fetch_feedback(conn, limit: int) -> list[dict]:
    """Recent feedback rows joined to their card, analogies first."""
    rows = conn.execute(
        """
        SELECT f.rating, f.comment, c.hook, c.body, c.format
        FROM card_feedback f
        JOIN cards c ON c.id = f.card_id
        ORDER BY (c.format = 'analogy') DESC, f.created_at DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [
        {"rating": r[0], "comment": r[1], "hook": r[2], "body": r[3], "format": r[4]}
        for r in rows
    ]


def _summarize(feedback: list[dict]) -> str:
    """Build a compact up/down digest for the LLM to reason over."""
    ups = [f for f in feedback if f["rating"] == "up"]
    downs = [f for f in feedback if f["rating"] == "down"]

    def block(items: list[dict], cap: int = 12) -> str:
        if not items:
            return "  (none)"
        lines = []
        for f in items[:cap]:
            hook = (f["hook"] or "").strip().replace("\n", " ")[:160]
            body = (f["body"] or "").strip().replace("\n", " ")[:240]
            line = f'  - [{f["format"]}] {hook} — {body}'
            if f["comment"]:
                line += f'\n      human comment: "{f["comment"].strip()[:200]}"'
            lines.append(line)
        return "\n".join(lines)

    return (
        f"UP-VOTED cards ({len(ups)}):\n{block(ups)}\n\n"
        f"DOWN-VOTED cards ({len(downs)}):\n{block(downs)}"
    )


def distill_lessons(feedback: list[dict], llm) -> list[str]:
    """Ask the LLM for 3-8 concrete, additive style lessons grounded in feedback."""
    digest = _summarize(feedback)
    prompt = f"""\
You are tuning the writing style of an analogy generator based on real human
feedback. Below are cards humans up-voted (liked) and down-voted (disliked),
plus any comments they left.

{digest}

Distill 3 to 8 CONCRETE, ADDITIVE style lessons for writing better analogies.
Rules:
- Ground every lesson in the ACTUAL feedback above — reference what up-voted
  cards did well and what down-voted cards / comments got wrong. No generic
  writing advice.
- Each lesson is one short imperative line ("Do X" / "Avoid Y").
- These get appended to a style guide, so make them additive and specific.

Respond with ONLY a JSON array of strings, e.g.:
["Lean into gym-culture analogies — they got the most up-votes", "Avoid restating the definition in the analogy opener"]
"""
    schema = {"type": "array", "items": {"type": "string"}}
    result = llm.generate(prompt, schema=schema)
    if isinstance(result, str):
        result = json.loads(result)
    if isinstance(result, dict):  # some providers wrap arrays
        for v in result.values():
            if isinstance(v, list):
                result = v
                break
    lessons = [str(x).strip() for x in result if str(x).strip()]
    return lessons[:8]


def _split_sections(text: str) -> tuple[str, list[str]]:
    """Return (foundation_before_learned_header, existing_learned_lesson_lines)."""
    if LEARNED_HEADER not in text:
        # No section yet — treat whole file as foundation, start fresh lessons.
        return text.rstrip() + "\n", []

    base, learned = text.split(LEARNED_HEADER, 1)
    existing: list[str] = []
    for line in learned.splitlines():
        s = line.strip()
        if not s or s.startswith("<!--") or s.startswith("(none"):
            continue
        if s.startswith("- (none"):
            continue
        if s.startswith("- "):
            existing.append(s[2:].strip())
    return base.rstrip() + "\n", existing


def merge_lessons(existing: list[str], new: list[str]) -> list[str]:
    """Dedup (case-insensitive) while preserving order; keep it reasonable."""
    seen = set()
    merged: list[str] = []
    for lesson in existing + new:
        key = lesson.lower().strip()
        if key and key not in seen:
            seen.add(key)
            merged.append(lesson)
    return merged[-40:]  # cap growth so the prompt stays bounded


def render(base: str, lessons: list[str]) -> str:
    body = "\n".join(f"- {l}" for l in lessons) if lessons else "- (none yet)"
    return (
        f"{base}\n"
        f"{LEARNED_HEADER}\n"
        f"{_MARKER_COMMENT} lessons below this line. -->\n"
        f"{body}\n"
    )


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 200

    path: Path = _SYSTEM_PROMPT_PATH
    current = path.read_text(encoding="utf-8")
    base, existing = _split_sections(current)

    with psycopg.connect(settings.database_url) as conn:
        feedback = fetch_feedback(conn, limit)

    if not feedback:
        print("No card feedback yet. Rate some cards in the feed first, then rerun.")
        return

    print(f"Considering {len(feedback)} feedback row(s) "
          f"({sum(f['rating'] == 'up' for f in feedback)} up / "
          f"{sum(f['rating'] == 'down' for f in feedback)} down)…\n")

    llm = get_llm()
    new_lessons = distill_lessons(feedback, llm)

    print("Proposed lessons:")
    for l in new_lessons:
        print(f"  + {l}")

    merged = merge_lessons(existing, new_lessons)

    print(f"\nLearned preferences: {len(existing)} before → {len(merged)} after "
          f"({len(merged) - len(existing):+d}).")

    if dry_run:
        print("\n--dry-run — analogy_system.md left unchanged.")
        return

    path.write_text(render(base, merged), encoding="utf-8")
    print(f"\nWrote {len(merged)} learned preference(s) into {path.name}.")
    print("Next `uv run generate` will use the updated voice.")
