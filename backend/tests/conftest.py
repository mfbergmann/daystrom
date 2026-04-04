"""Test fixtures: in-memory SQLite database, test client, mocked AI services."""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, Column, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Override settings BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["PIN"] = ""

from app.core.config import settings
settings.pin = ""

from app.core.database import Base, get_db
import app.core.database as db_module

# Monkey-patch Vector columns to Text for SQLite compatibility
from pgvector.sqlalchemy import Vector
_orig_vector_init = Vector.__init__

# Patch all models' Vector columns to be nullable Text for SQLite
import app.models  # noqa: ensure all models loaded


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _make_sqlite_compatible_metadata():
    """Replace PostgreSQL-specific column types with SQLite-compatible ones for testing."""
    from sqlalchemy.dialects.postgresql import JSONB, UUID
    from sqlalchemy import Text, String

    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, Vector):
                col.type = Text()
            elif isinstance(col.type, JSONB):
                col.type = Text()
            elif isinstance(col.type, UUID):
                col.type = String(36)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    _make_sqlite_compatible_metadata()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(test_session_factory):
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine, test_session_factory):
    """FastAPI test client with DB override and mocked AI/Redis."""
    # Patch the engine so the app lifespan uses our test engine
    original_engine = db_module.engine
    db_module.engine = test_engine

    from app.main import app

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.workers.enrichment.enqueue_enrichment", new_callable=AsyncMock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
    db_module.engine = original_engine
