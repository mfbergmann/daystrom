"""Daystrom v2 — Intelligent Todo & Idea Capture."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.routers import items, tags, search, events, auth, health, memory, learning, chat, agent_tasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Daystrom v2 started")
    yield
    logger.info("Daystrom v2 shutting down")


app = FastAPI(
    title="Daystrom",
    description="Intelligent todo & idea capture that learns from you",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(tags.router)
app.include_router(search.router)
app.include_router(events.router)
app.include_router(memory.router)
app.include_router(learning.router)
app.include_router(chat.router)
app.include_router(agent_tasks.router)


@app.get("/")
async def root():
    return {"name": "Daystrom", "version": "2.0.0", "status": "running"}
