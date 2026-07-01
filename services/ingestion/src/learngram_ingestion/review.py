"""
Manual approval CLI for graph extension proposals.

Usage:  uv run review [--status pending|approved|rejected] [--kind node|edge]
        uv run review --stats

Controls:
  a  approve as-is
  e  edit fields then approve
  r  reject
  s  skip (leave pending)
  q  quit
"""
import json
import sys
import uuid
from datetime import datetime, timezone

import psycopg
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from learngram_shared.config import settings
from .graph_ops import approve_node, approve_edge

console = Console()

VALID_TOPICS = ["networking", "caching", "databases", "distributed-systems", "consistency", "messaging"]
VALID_REL    = ["prerequisite_of", "alternative_to", "used_in", "example_of",
                "trades_off_with", "related_to", "evolved_from"]


# ── Display helpers ────────────────────────────────────────────────────────────

def _render_node_proposal(payload: dict, doc_title: str) -> Panel:
    t = Table.grid(padding=(0, 2))
    t.add_row(Text("name",        style="dim"), Text(payload.get("name", "?"),        style="bold white"))
    t.add_row(Text("slug",        style="dim"), Text(payload.get("slug", "?"),        style="cyan"))
    t.add_row(Text("topic",       style="dim"), Text(payload.get("topic", "?"),       style="yellow"))
    t.add_row(Text("depth",       style="dim"), Text(str(payload.get("depth_level", "?"))))
    t.add_row(Text("description", style="dim"), Text(payload.get("short_description", ""), style="white"))
    t.add_row(Text("source",      style="dim"), Text(doc_title[:80],                  style="dim italic"))
    return Panel(t, title="[bold]NODE proposal[/bold]", border_style="blue", box=box.ROUNDED)


def _render_edge_proposal(payload: dict, doc_title: str, existing_nodes: dict[str, str]) -> Panel:
    fs = payload.get("from_slug", "?")
    ts = payload.get("to_slug",   "?")
    fn = existing_nodes.get(fs, fs)
    tn = existing_nodes.get(ts, ts)
    t = Table.grid(padding=(0, 2))
    t.add_row(Text("from",         style="dim"), Text(f"{fn} ({fs})", style="bold white"))
    t.add_row(Text("→ to",         style="dim"), Text(f"{tn} ({ts})", style="bold white"))
    t.add_row(Text("relationship", style="dim"), Text(payload.get("relationship_type", "?"), style="yellow"))
    t.add_row(Text("weight",       style="dim"), Text(str(payload.get("weight", 1.0))))
    t.add_row(Text("source",       style="dim"), Text(doc_title[:80], style="dim italic"))
    return Panel(t, title="[bold]EDGE proposal[/bold]", border_style="magenta", box=box.ROUNDED)


# ── Edit helpers ───────────────────────────────────────────────────────────────

def _edit_node(payload: dict) -> dict:
    p = dict(payload)
    console.print("\n[dim]Press Enter to keep current value.[/dim]")
    for field, choices in [
        ("name",              None),
        ("slug",              None),
        ("short_description", None),
        ("topic",             VALID_TOPICS),
        ("depth_level",       None),
    ]:
        current = p.get(field, "")
        hint    = f" [{', '.join(choices)}]" if choices else ""
        val     = input(f"  {field}{hint} [{current}]: ").strip()
        if val:
            p[field] = int(val) if field == "depth_level" else val
    return p


def _edit_edge(payload: dict) -> dict:
    p = dict(payload)
    console.print("\n[dim]Press Enter to keep current value.[/dim]")
    for field, choices in [
        ("from_slug",         None),
        ("to_slug",           None),
        ("relationship_type", VALID_REL),
        ("weight",            None),
    ]:
        current = p.get(field, "")
        hint    = f" [{', '.join(choices)}]" if choices else ""
        val     = input(f"  {field}{hint} [{current}]: ").strip()
        if val:
            p[field] = float(val) if field == "weight" else val
    return p


# ── Reject action ──────────────────────────────────────────────────────────────
# (approve_node / approve_edge live in graph_ops so the auto pipeline can reuse them)

def _reject(conn: psycopg.Connection, proposal_id: uuid.UUID) -> None:
    conn.execute(
        "UPDATE proposals SET status='rejected', reviewed_at=%s WHERE id=%s",
        (datetime.now(timezone.utc), proposal_id),
    )
    conn.commit()


# ── Stats ──────────────────────────────────────────────────────────────────────

def _show_stats(conn: psycopg.Connection) -> None:
    rows = conn.execute(
        """
        SELECT kind, status, count(*) FROM proposals
        GROUP BY kind, status ORDER BY kind, status
        """
    ).fetchall()
    t = Table(title="Proposal stats", box=box.SIMPLE_HEAVY)
    t.add_column("kind");  t.add_column("status"); t.add_column("count", justify="right")
    for r in rows:
        t.add_row(r[0], r[1], str(r[2]))
    console.print(t)
    node_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
    console.print(f"Graph: [bold]{node_count}[/bold] nodes · [bold]{edge_count}[/bold] edges")


# ── Main loop ──────────────────────────────────────────────────────────────────

def main() -> None:
    args       = sys.argv[1:]
    show_stats = "--stats" in args
    filt_status = args[args.index("--status") + 1] if "--status" in args else "pending"
    filt_kind   = args[args.index("--kind")   + 1] if "--kind"   in args else None

    with psycopg.connect(settings.database_url) as conn:
        if show_stats:
            _show_stats(conn)
            return

        # Load all known node slugs → names for display
        existing_nodes: dict[str, str] = {
            r[0]: r[1] for r in conn.execute("SELECT slug, name FROM nodes").fetchall()
        }

        # Load proposals
        query = """
            SELECT p.id, p.kind, p.payload, p.document_id, COALESCE(d.title, '(unknown)') as doc_title
            FROM proposals p
            LEFT JOIN documents d ON d.id = p.document_id
            WHERE p.status = %s
        """
        params: list = [filt_status]
        if filt_kind:
            query += " AND p.kind = %s"
            params.append(filt_kind)
        query += " ORDER BY p.created_at"

        proposals = conn.execute(query, params).fetchall()

    if not proposals:
        console.print(f"[dim]No {filt_status} proposals found.[/dim]")
        return

    console.print(f"\n[bold]{len(proposals)}[/bold] {filt_status} proposal(s)  "
                  f"[dim]a=approve  e=edit+approve  r=reject  s=skip  q=quit[/dim]\n")

    with psycopg.connect(settings.database_url) as conn:
        for idx, (prop_id, kind, payload, doc_id, doc_title) in enumerate(proposals, 1):
            console.rule(f"[dim]{idx}/{len(proposals)}[/dim]")

            if kind == "node":
                console.print(_render_node_proposal(payload, doc_title))
            else:
                # Add any newly approved node slugs to existing_nodes dict for edge display
                fresh = {r[0]: r[1] for r in conn.execute("SELECT slug, name FROM nodes").fetchall()}
                existing_nodes.update(fresh)
                console.print(_render_edge_proposal(payload, doc_title, existing_nodes))

            action = input("\n> ").strip().lower()

            if action == "q":
                console.print("[dim]Exiting.[/dim]")
                break
            elif action == "s":
                console.print("[dim]Skipped.[/dim]")
                continue
            elif action == "r":
                _reject(conn, prop_id)
                console.print("[red]Rejected.[/red]")
            elif action == "a":
                if kind == "node":
                    approve_node(conn, prop_id, payload, doc_id)
                    existing_nodes[payload["slug"]] = payload["name"]
                    console.print("[green]Approved.[/green]")
                elif approve_edge(conn, prop_id, payload):
                    console.print("[green]Approved.[/green]")
                else:
                    console.print("[red]Cannot approve: endpoint node not found — left pending.[/red]")
            elif action == "e":
                edited = _edit_node(payload) if kind == "node" else _edit_edge(payload)
                if kind == "node":
                    approve_node(conn, prop_id, edited, doc_id)
                    existing_nodes[edited["slug"]] = edited["name"]
                    console.print("[green]Edited & approved.[/green]")
                elif approve_edge(conn, prop_id, edited):
                    console.print("[green]Edited & approved.[/green]")
                else:
                    console.print("[red]Cannot approve: endpoint node not found — left pending.[/red]")
            else:
                console.print("[dim]Unknown key — skipped.[/dim]")

    console.print("\nRun [bold]uv run review --stats[/bold] to see totals.")
