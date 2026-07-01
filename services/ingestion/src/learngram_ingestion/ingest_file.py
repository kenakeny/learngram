"""
Ingest a local file (Markdown / PDF / DOCX / …) into the pipeline.

Converts non-Markdown files to Markdown with markitdown, splits into document
sections, inserts them, then runs the full auto pipeline (extract → approve →
embed → generate) so the file turns straight into feed cards.

Usage:
  uv run ingest-file <path>              # one file
  uv run ingest-file <dir>               # every supported file under a directory
  uv run ingest-file a.pdf b.md          # multiple
  uv run ingest-file <path> --land-only  # insert documents but skip the pipeline
"""
import os
import sys
import tempfile
from pathlib import Path

import psycopg

from learngram_shared.config import settings

from .pipeline import run_pipeline
from .text_utils import detect_topics, slug_anchor, split_markdown_by_h2

# Passed through as-is; everything else goes through markitdown.
MARKDOWN_EXTS = {".md", ".markdown", ".txt"}
# What a directory scan will pick up.
SUPPORTED_EXTS = MARKDOWN_EXTS | {".pdf", ".docx", ".pptx", ".html", ".htm"}


def to_markdown(filename: str, data: bytes) -> str:
    """Return Markdown text for a file's bytes, converting via markitdown if needed."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in MARKDOWN_EXTS:
        return data.decode("utf-8", errors="replace")

    try:
        from markitdown import MarkItDown
    except ImportError as e:
        raise ImportError("Install markitdown: uv add --package learngram-ingestion markitdown") from e

    # markitdown converts from a path; write to a temp file with the right suffix.
    with tempfile.NamedTemporaryFile(suffix=ext or ".bin", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        return MarkItDown().convert(tmp_path).text_content or ""
    finally:
        os.unlink(tmp_path)


def ingest_bytes(conn: psycopg.Connection, filename: str, data: bytes) -> list:
    """Convert + split + insert a file into `documents`. Returns NEW document ids.

    Sections already present (same synthetic source_url) are skipped, so
    re-ingesting the same file is a no-op.
    """
    markdown = to_markdown(filename, data)
    if not markdown.strip():
        return []

    sections = split_markdown_by_h2(markdown)
    if not sections:
        # No H2 structure (common for converted PDFs) — treat the whole file as one doc.
        title = os.path.splitext(os.path.basename(filename))[0]
        sections = [{"heading": title, "body": markdown.strip(), "anchor": slug_anchor(title)}]

    new_ids: list = []
    for sec in sections:
        source_url = f"upload://{filename}#{sec['anchor']}"
        if conn.execute("SELECT 1 FROM documents WHERE source_url = %s", (source_url,)).fetchone():
            continue
        topics = detect_topics(sec["heading"] + " " + sec["body"], default=["distributed-systems"])
        row = conn.execute(
            """
            INSERT INTO documents (source_url, source_type, title, cleaned_text, topic_tags)
            VALUES (%s, 'upload', %s, %s, %s)
            RETURNING id
            """,
            (source_url, sec["heading"], sec["body"], topics),
        ).fetchone()
        conn.commit()
        new_ids.append(row[0])
    return new_ids


def _collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files += [f for f in sorted(path.rglob("*")) if f.suffix.lower() in SUPPORTED_EXTS]
        elif path.is_file():
            files.append(path)
        else:
            print(f"  skip (not found): {p}")
    return files


def main() -> None:
    args = sys.argv[1:]
    land_only = "--land-only" in args
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print("usage: uv run ingest-file <path|dir> [more…] [--land-only]")
        sys.exit(1)

    files = _collect_files(paths)
    if not files:
        print("No supported files found.")
        return

    with psycopg.connect(settings.database_url) as conn:
        all_doc_ids: list = []
        for f in files:
            print(f"\n→ {f.name}")
            ids = ingest_bytes(conn, f.name, f.read_bytes())
            print(f"  {len(ids)} new document section(s)")
            all_doc_ids += ids

        if not all_doc_ids:
            print("\nNothing new to process (already ingested?).")
            return

        if land_only:
            print(f"\nLanded {len(all_doc_ids)} section(s). Run extract/embed/generate yourself.")
            return

        print(f"\nRunning pipeline over {len(all_doc_ids)} section(s)…")
        summary = run_pipeline(conn, all_doc_ids, progress=lambda step, msg: print(f"  [{step}] {msg}"))

    print(
        f"\nDone. +{summary['nodes_added']} concepts, "
        f"+{summary['edges_added']} links, +{summary['cards_added']} cards."
    )
    print("Open the feed to see them.")
