"""Forward-only migration runner. Run with: uv run migrate"""
import sys
from pathlib import Path
import psycopg
from ..config import settings


def main() -> None:
    migrations_dir = Path.cwd() / "db" / "migrations"
    if not migrations_dir.exists():
        print(f"ERROR: migrations directory not found at {migrations_dir}", file=sys.stderr)
        print("Run this command from the repo root.", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(settings.database_url, autocommit=False) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()

        pending = 0
        for migration in sorted(migrations_dir.glob("*.sql")):
            filename = migration.name
            already_applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,)
            ).fetchone()
            if already_applied:
                print(f"  skip  {filename}")
                continue

            print(f"  apply {filename} ...", end=" ", flush=True)
            conn.execute(migration.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,))
            conn.commit()
            print("ok")
            pending += 1

    print(f"\n{pending} migration(s) applied.")
