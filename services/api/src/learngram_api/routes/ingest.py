"""Upload a file and turn it into feed cards via the auto pipeline.

POST /ingest        multipart file → creates a job, processes in the background
GET  /ingest/{id}   poll job status/progress

The pipeline makes many local-LLM calls (can take minutes), so it runs as a
FastAPI background task (a sync function → threadpool, off the event loop) while
the frontend polls the job row for progress.
"""
import psycopg
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from learngram_shared.config import settings
from learngram_shared.db.pool import get_pool
from learngram_ingestion.ingest_file import ingest_bytes
from learngram_ingestion.pipeline import run_pipeline

from ..models import IngestJob

router = APIRouter()

_JOB_COLS = ("status", "step", "message", "nodes_added", "cards_added")


def _run_job(job_id: str, filename: str, data: bytes) -> None:
    """Background worker: convert → extract → approve → embed → generate."""
    status_conn = psycopg.connect(settings.database_url, autocommit=True)

    def set_status(**fields) -> None:
        sets = [f"{k} = %s" for k in _JOB_COLS if fields.get(k) is not None]
        vals = [fields[k] for k in _JOB_COLS if fields.get(k) is not None]
        if fields.get("status") in ("done", "error"):
            sets.append("finished_at = NOW()")
        vals.append(job_id)
        status_conn.execute(f"UPDATE ingest_jobs SET {', '.join(sets)} WHERE id = %s", vals)

    try:
        set_status(status="running", step="convert", message="converting file")
        with psycopg.connect(settings.database_url) as conn:
            doc_ids = ingest_bytes(conn, filename, data)
            if not doc_ids:
                set_status(status="done", step="done",
                           message="No new content found (already ingested?).")
                return
            summary = run_pipeline(
                conn, doc_ids,
                progress=lambda step, msg: set_status(step=step, message=msg),
            )
        set_status(
            status="done", step="done",
            message=f"+{summary['nodes_added']} concepts, +{summary['cards_added']} cards",
            nodes_added=summary["nodes_added"], cards_added=summary["cards_added"],
        )
    except Exception as e:  # noqa: BLE001 — surface any failure to the job row
        set_status(status="error", step="error", message=str(e)[:500])
    finally:
        status_conn.close()


@router.post("/ingest")
async def create_ingest(background: BackgroundTasks, file: UploadFile = File(...)) -> dict:
    data = await file.read()
    filename = file.filename or "upload.bin"
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    pool = get_pool()
    with pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO ingest_jobs (filename) VALUES (%s) RETURNING id", (filename,)
        ).fetchone()
    job_id = str(row[0])

    background.add_task(_run_job, job_id, filename, data)
    return {"job_id": job_id, "filename": filename}


@router.get("/ingest/{job_id}", response_model=IngestJob)
async def get_ingest(job_id: str) -> IngestJob:
    pool = get_pool()
    with pool.connection() as conn:
        r = conn.execute(
            "SELECT id, filename, status, step, message, nodes_added, cards_added "
            "FROM ingest_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="job not found")
    return IngestJob(
        id=str(r[0]), filename=r[1], status=r[2], step=r[3],
        message=r[4], nodes_added=r[5], cards_added=r[6],
    )
