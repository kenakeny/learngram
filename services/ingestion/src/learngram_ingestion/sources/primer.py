"""
Ingest the System Design Primer into `documents`.

Downloads donnemartin/system-design-primer as a zip, walks all .md files,
splits each file by H2 (##) sections, and upserts each section as a document.

Usage:  uv run ingest-primer
"""
import io
import sys
import zipfile
from pathlib import PurePosixPath

import httpx
import psycopg

from learngram_shared.config import settings
from ..text_utils import detect_topics, split_markdown_by_h2

REPO_ZIP = "https://github.com/donnemartin/system-design-primer/archive/refs/heads/master.zip"
BASE_URL  = "https://github.com/donnemartin/system-design-primer/blob/master"


def _split_by_h2(path_in_zip: str, content: str) -> list[dict]:
    """Split a markdown file into H2 sections, return list of section dicts."""
    rel_path = "/".join(PurePosixPath(path_in_zip).parts[1:])  # strip repo root dir
    sections = []
    for sec in split_markdown_by_h2(content):
        sections.append({
            "source_url":   f"{BASE_URL}/{rel_path}#{sec['anchor']}",
            "title":        sec["heading"],
            "cleaned_text": sec["body"],
            "topic_tags":   detect_topics(sec["heading"] + " " + sec["body"], default=["distributed-systems"]),
        })
    return sections


def main() -> None:
    print("Downloading System Design Primer …", flush=True)
    try:
        resp = httpx.get(REPO_ZIP, follow_redirects=True, timeout=120)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"ERROR: failed to download primer: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Downloaded {len(resp.content) / 1_048_576:.1f} MB. Parsing …")

    sections: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        md_files = [n for n in zf.namelist() if n.endswith(".md") and "__pycache__" not in n]
        for name in sorted(md_files):
            try:
                content = zf.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue
            sections.extend(_split_by_h2(name, content))

    print(f"  Parsed {len(sections)} sections from {len(md_files)} markdown files.")

    inserted = skipped = 0
    with psycopg.connect(settings.database_url) as conn:
        for s in sections:
            exists = conn.execute(
                "SELECT 1 FROM documents WHERE source_url = %s", (s["source_url"],)
            ).fetchone()
            if exists:
                skipped += 1
                continue
            conn.execute(
                """
                INSERT INTO documents (source_url, source_type, title, cleaned_text, topic_tags)
                VALUES (%s, 'primer', %s, %s, %s)
                """,
                (s["source_url"], s["title"], s["cleaned_text"], s["topic_tags"]),
            )
            inserted += 1
        conn.commit()

    print(f"\nDone. inserted={inserted}  skipped={skipped} (already present)")
