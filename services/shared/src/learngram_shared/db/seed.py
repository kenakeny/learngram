"""Seed runner. Run with: uv run seed"""
import sys
from pathlib import Path
import psycopg
from ..config import settings


def main() -> None:
    seed_dir = Path.cwd() / "db" / "seed"
    if not seed_dir.exists():
        print(f"ERROR: seed directory not found at {seed_dir}", file=sys.stderr)
        print("Run this command from the repo root.", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(settings.database_url, autocommit=False) as conn:
        for seed_file in sorted(seed_dir.glob("*.sql")):
            print(f"  seeding {seed_file.name} ...", end=" ", flush=True)
            conn.execute(seed_file.read_text(encoding="utf-8"))
            conn.commit()
            print("ok")

    # Quick sanity check
    with psycopg.connect(settings.database_url) as conn:
        node_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]

    print(f"\nDone. nodes={node_count}  edges={edge_count}")
