"""Embedding generation and semantic search via pgvector."""

import logging
from uuid import UUID

from sqlalchemy import select, text, func, case, literal
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


async def hybrid_search(
    db: AsyncSession,
    query: str,
    limit: int = 20,
    vector_weight: float = 0.7,
    text_weight: float = 0.3,
) -> list[tuple[Item, float]]:
    """Hybrid search combining pgvector cosine similarity with PostgreSQL full-text search.

    Returns (item, combined_score) tuples, where higher score = better match.
    """
    query_embedding = await embed_text(query)

    # Vector similarity score (1 - cosine_distance, so higher = better)
    vector_score = (literal(1.0) - Item.embedding.cosine_distance(query_embedding)).label("vector_score")

    # Full-text search score using ts_rank
    ts_query = func.plainto_tsquery("english", query)
    ts_vector = func.to_tsvector("english", Item.content)
    text_score = func.ts_rank(ts_vector, ts_query).label("text_score")

    # Combined weighted score
    combined = (vector_weight * vector_score + text_weight * text_score).label("score")

    stmt = (
        select(Item, combined)
        .where(
            # Must match at least one: vector similarity OR text match
            (Item.embedding.isnot(None) & (Item.embedding.cosine_distance(query_embedding) < 0.5))
            | (func.to_tsvector("english", Item.content).op("@@")(ts_query))
        )
        .order_by(combined.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    return [(row.Item, float(row.score)) for row in result]


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
