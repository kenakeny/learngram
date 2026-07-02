from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from learngram_shared.db.pool import get_pool, close_pool
from .routes.health import router as health_router
from .routes.feed import router as feed_router
from .routes.graph import router as graph_router
from .routes.ingest import router as ingest_router
from .routes.feedback import router as feedback_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()  # open on startup
    yield
    close_pool()


app = FastAPI(title="learngram API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(feed_router)
app.include_router(graph_router)
app.include_router(ingest_router)
app.include_router(feedback_router)
