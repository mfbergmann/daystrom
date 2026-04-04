"""Embedding generation and semantic search via pgvector."""

import logging
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.item import Item
from app.services.ai_service import generate_embedding

logger = logging.getLogger(__name__)


async def embed_text(content: str) -> list[float]:
    """Generate embedding vector for text content."""
    return await generate_embedding(content)


async def semantic_search(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    threshold: float | None = None,
    exclude_ids: list[UUID] | None = None,
) -> list[tuple[Item, float]]:
    """Search items by semantic similarity. Returns (item, distance) tuples."""
    threshold = threshold or settings.similarity_threshold
    query_embedding = await embed_text(query)

    # pgvector cosine distance: smaller = more similar
    distance_expr = Item.embedding.cosine_distance(query_embedding)

    stmt = (
        select(Item, distance_expr.label("distance"))
        .where(Item.embedding.isnot(None))
        .where(distance_expr < (1 - threshold))  # cosine_distance = 1 - similarity
        .order_by(distance_expr)
        .limit(limit)
    )

    if exclude_ids:
        stmt = stmt.where(Item.id.notin_(exclude_ids))

    result = await db.execute(stmt)
    return [(row.Item, row.distance) for row in result]


async def find_similar_items(
    db: AsyncSession,
    item: Item,
    limit: int = 5,
) -> list[tuple[Item, float]]:
    """Find items similar to a given item using its embedding."""
    if item.embedding is None:
        return []

    distance_expr = Item.embedding.cosine_distance(item.embedding)

    stmt = (
        select(Item, distance_expr.label("distance"))
        .where(Item.embedding.isnot(None))
        .where(Item.id != item.id)
        .where(distance_expr < 0.3)  # high similarity only
        .order_by(distance_expr)
        .limit(limit)
    )

    result = await db.execute(stmt)
    return [(row.Item, row.distance) for row in result]
