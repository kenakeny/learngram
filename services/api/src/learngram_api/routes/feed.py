import random
from fastapi import APIRouter, Query
from learngram_shared.db.pool import get_pool
from ..models import FeedCard, FeedResponse

router = APIRouter()


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(default=20, ge=1, le=100),
    seed: int = Query(default=0),
) -> FeedResponse:
    pool = get_pool()
    with pool.connection() as conn:
        # Phase 1: check if cards table has rows; fall back to nodes
        card_count = conn.execute("SELECT count(*) FROM cards").fetchone()[0]

        if card_count > 0:
            rows = conn.execute(
                """
                SELECT c.id, c.node_id, n.slug, n.topic, c.hook, c.body, c.format
                FROM cards c
                JOIN nodes n ON n.id = c.node_id
                ORDER BY random()
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
            cards = [
                FeedCard(
                    id=str(r[0]),
                    node_id=str(r[1]),
                    node_slug=r[2],
                    topic=r[3],
                    hook=r[4],
                    body=r[5],
                    format=r[6],
                )
                for r in rows
            ]
        else:
            # Phase 1 placeholder: project nodes as cards
            rows = conn.execute(
                "SELECT id, slug, topic, name, short_description FROM nodes",
            ).fetchall()

            rng = random.Random(seed if seed != 0 else None)
            rng.shuffle(rows)
            rows = rows[:limit]

            cards = [
                FeedCard(
                    id=str(r[0]),
                    node_id=str(r[0]),
                    node_slug=r[1],
                    topic=r[2],
                    hook=r[3],
                    body=r[4],
                    format="pattern",
                )
                for r in rows
            ]

    return FeedResponse(cards=cards, seed=seed)
