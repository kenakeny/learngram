import random
from fastapi import APIRouter, Query
from pydantic import BaseModel
from learngram_shared.db.pool import get_pool
from ..models import FeedCard, FeedResponse, Persona

router = APIRouter()


class TopicCount(BaseModel):
    topic: str
    cards: int
    nodes: int


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(default=20, ge=1, le=100),
    seed: int = Query(default=0),
    topic: str | None = Query(default=None),
    persona: str | None = Query(default=None),
) -> FeedResponse:
    pool = get_pool()
    with pool.connection() as conn:
        # Phase 1: check if cards table has rows; fall back to nodes
        card_count = conn.execute("SELECT count(*) FROM cards").fetchone()[0]

        if card_count > 0:
            # Once persona posts exist, the feed IS the accounts feed.
            has_persona = conn.execute(
                "SELECT EXISTS(SELECT 1 FROM cards WHERE persona_id IS NOT NULL)"
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT c.id, c.node_id, n.slug, n.topic, c.hook, c.body, c.format,
                       c.post_style, p.slug, p.display_name, p.accent_color, p.avatar_emoji, n.name
                FROM cards c
                JOIN nodes n ON n.id = c.node_id
                LEFT JOIN personas p ON p.id = c.persona_id
                WHERE (%s::text IS NULL OR n.topic = %s)
                  AND (%s::text IS NULL OR p.slug = %s)
                  {"AND c.persona_id IS NOT NULL" if has_persona else ""}
                ORDER BY random()
                LIMIT %s
                """,
                (topic, topic, persona, persona, limit),
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
                    post_style=r[7],
                    persona_slug=r[8],
                    persona_name=r[9],
                    persona_color=r[10],
                    persona_emoji=r[11],
                    concept_name=r[12],
                )
                for r in rows
            ]
        else:
            # Phase 1 placeholder: project nodes as cards
            rows = conn.execute(
                """
                SELECT id, slug, topic, name, short_description
                FROM nodes
                WHERE (%s::text IS NULL OR topic = %s)
                """,
                (topic, topic),
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


@router.get("/topics", response_model=list[TopicCount])
async def get_topics() -> list[TopicCount]:
    pool = get_pool()
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT n.topic,
                   count(DISTINCT c.id) AS cards,
                   count(DISTINCT n.id) AS nodes
            FROM nodes n
            LEFT JOIN cards c ON c.node_id = n.id
            WHERE n.topic IS NOT NULL
            GROUP BY n.topic
            ORDER BY cards DESC, nodes DESC
            """,
        ).fetchall()

    return [TopicCount(topic=r[0], cards=r[1], nodes=r[2]) for r in rows]


@router.get("/personas", response_model=list[Persona])
async def get_personas() -> list[Persona]:
    pool = get_pool()
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT p.slug, p.display_name, p.bio, p.post_style, p.accent_color, p.avatar_emoji,
                   count(c.id) AS posts
            FROM personas p
            LEFT JOIN cards c ON c.persona_id = p.id
            GROUP BY p.id
            ORDER BY posts DESC, p.slug
            """
        ).fetchall()
    return [
        Persona(slug=r[0], display_name=r[1], bio=r[2], post_style=r[3],
                accent_color=r[4], avatar_emoji=r[5], posts=r[6])
        for r in rows
    ]
