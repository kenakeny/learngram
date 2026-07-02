"""Capture human feedback (👍 / 👎 + optional comment) on generated cards.

POST /feedback   {card_id, rating: 'up'|'down', comment?}  → inserts a row.

Feeds the RLHF-style tuning loop: rate cards → `uv run tune-analogies` distills
the feedback into services/ingestion/.../prompts/analogy_system.md → the next
`uv run generate` uses the improved voice.
"""
from fastapi import APIRouter, HTTPException

from learngram_shared.db.pool import get_pool

from ..models import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(req: FeedbackRequest) -> FeedbackResponse:
    pool = get_pool()
    with pool.connection() as conn:
        card = conn.execute(
            "SELECT node_id FROM cards WHERE id = %s", (req.card_id,)
        ).fetchone()
        if not card:
            raise HTTPException(status_code=404, detail="card not found")
        node_id = card[0]

        row = conn.execute(
            """
            INSERT INTO card_feedback (card_id, node_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (req.card_id, node_id, req.rating, req.comment),
        ).fetchone()

    return FeedbackResponse(
        id=str(row[0]),
        card_id=req.card_id,
        node_id=str(node_id) if node_id else None,
        rating=req.rating,
    )
