from fastapi import APIRouter
from learngram_shared.db.pool import get_pool

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    try:
        pool = get_pool()
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "db": db_ok}
