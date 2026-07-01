"""
Ingest engineering blog posts via RSS → trafilatura.

Usage:  uv run ingest-blogs [--limit N]
"""
import sys
import time

import feedparser
import httpx
import psycopg
import trafilatura

from learngram_shared.config import settings
from ..text_utils import detect_topics

RSS_FEEDS = [
    ("High Scalability",    "http://feeds.feedburner.com/HighScalability"),
    ("Cloudflare Blog",     "https://blog.cloudflare.com/rss/"),
    ("Netflix Tech Blog",   "https://netflixtechblog.com/feed"),
]


def _fetch_article(url: str) -> str | None:
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30,
                         headers={"User-Agent": "learngram-ingestion/0.1"})
        resp.raise_for_status()
        return trafilatura.extract(resp.text, include_comments=False, include_tables=False)
    except Exception:
        return None


def main(limit: int = 20) -> None:
    # Parse --limit from argv
    args = sys.argv[1:]
    if "--limit" in args:
        try:
            limit = int(args[args.index("--limit") + 1])
        except (IndexError, ValueError):
            pass

    total_inserted = total_skipped = 0

    with psycopg.connect(settings.database_url) as conn:
        for feed_name, feed_url in RSS_FEEDS:
            print(f"\nFeed: {feed_name} …", flush=True)
            try:
                feed = feedparser.parse(feed_url)
            except Exception as e:
                print(f"  ERROR parsing feed: {e}")
                continue

            entries = feed.entries[:limit]
            print(f"  {len(entries)} entries")

            for entry in entries:
                url   = entry.get("link", "")
                title = entry.get("title", "")
                if not url or not title:
                    continue

                exists = conn.execute(
                    "SELECT 1 FROM documents WHERE source_url = %s", (url,)
                ).fetchone()
                if exists:
                    total_skipped += 1
                    print(f"  skip  {title[:60]}")
                    continue

                print(f"  fetch {title[:60]} …", end=" ", flush=True)
                text = _fetch_article(url)
                if not text or len(text) < 300:
                    print("too short / failed")
                    continue

                topics = detect_topics(title + " " + text)
                if not topics:
                    print("off-topic")
                    continue

                conn.execute(
                    """
                    INSERT INTO documents (source_url, source_type, title, cleaned_text, topic_tags)
                    VALUES (%s, 'blog', %s, %s, %s)
                    """,
                    (url, title, text, topics),
                )
                conn.commit()
                total_inserted += 1
                print(f"ok ({len(text):,} chars)")
                time.sleep(0.5)  # be polite

    print(f"\nDone. inserted={total_inserted}  skipped={total_skipped}")
