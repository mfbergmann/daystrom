"""Learning service — pattern detection, tag affinity, classification refinement.

Analyzes user interactions to build a behavioral model that improves over time.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.interaction import Interaction, InteractionType
from app.models.item import Item, ItemType
from app.models.item_tag import ItemTag, TagSource
from app.models.tag import Tag
from app.models.memory import MemoryFact
from app.models.association import Association, AssociationType, AssociationSource
from app.services.embedding_service import find_similar_items
from app.services.ai_service import generate_embedding

logger = logging.getLogger(__name__)


async def compute_tag_affinity(db: AsyncSession) -> dict[str, float]:
    """Compute acceptance rate for AI-suggested tags.

    Returns {tag_name: acceptance_rate} where 1.0 = always kept, 0.0 = always removed.
    """
    # Get all AI-assigned tags
    stmt = (
        select(Tag.name, func.count(ItemTag.id).label("total"))
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .where(ItemTag.source == TagSource.ai)
        .group_by(Tag.name)
    )
    result = await db.execute(stmt)
    ai_tag_counts = {row.name: row.total for row in result}

    # Get rejected tags from interactions
    stmt = (
        select(Interaction.context)
        .where(Interaction.interaction_type == InteractionType.tag_rejected)
    )
    result = await db.execute(stmt)
    rejections = Counter()
    for row in result.scalars():
        if row and "tag_name" in row:
            rejections[row["tag_name"]] += 1

    affinity = {}
    for tag_name, total in ai_tag_counts.items():
        rejected = rejections.get(tag_name, 0)
        affinity[tag_name] = max(0.0, 1.0 - (rejected / max(total, 1)))

    return affinity


async def get_classification_corrections(db: AsyncSession, days: int = 30) -> list[dict]:
    """Get recent classification corrections as few-shot examples."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(Interaction, Item.content)
        .join(Item, Item.id == Interaction.item_id)
        .where(Interaction.interaction_type == InteractionType.classification_corrected)
        .where(Interaction.created_at > since)
        .order_by(Interaction.created_at.desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    corrections = []
    for interaction, content in result:
        ctx = interaction.context or {}
        corrections.append({
            "content": content[:200],
            "was_classified_as": ctx.get("old"),
            "corrected_to": ctx.get("new"),
        })
    return corrections


async def get_behavioral_model(db: AsyncSession) -> dict:
    """Build a behavioral model from interaction history."""
    model = {}

    # Time-of-day patterns for capture
    stmt = select(
        func.extract("hour", Item.created_at).label("hour"),
        func.count(Item.id).label("count"),
    ).group_by("hour").order_by("hour")
    result = await db.execute(stmt)
    model["capture_hours"] = {int(row.hour): row.count for row in result}

    # Type distribution
    stmt = select(Item.item_type, func.count(Item.id)).group_by(Item.item_type)
    result = await db.execute(stmt)
    model["type_distribution"] = {
        (row[0].value if row[0] else "none"): row[1] for row in result
    }

    # Completion rate
    total_tasks = await db.scalar(
        select(func.count(Item.id)).where(Item.item_type == ItemType.task)
    ) or 0
    completed_tasks = await db.scalar(
        select(func.count(Item.id)).where(
            and_(Item.item_type == ItemType.task, Item.completed_at.isnot(None))
        )
    ) or 0
    model["task_completion_rate"] = completed_tasks / max(total_tasks, 1)

    # Average completion time (hours)
    stmt = select(
        func.avg(
            func.extract("epoch", Item.completed_at - Item.created_at) / 3600
        )
    ).where(Item.completed_at.isnot(None))
    avg_hours = await db.scalar(stmt)
    model["avg_completion_hours"] = round(float(avg_hours), 1) if avg_hours else None

    # Tag affinity
    model["tag_affinity"] = await compute_tag_affinity(db)

    # Classification corrections count
    corrections_count = await db.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.interaction_type == InteractionType.classification_corrected
        )
    ) or 0
    model["classification_corrections"] = corrections_count

    # Memory facts count
    memory_count = await db.scalar(
        select(func.count(MemoryFact.id)).where(MemoryFact.confidence > 0.1)
    ) or 0
    model["active_memories"] = memory_count

    return model


async def discover_associations(db: AsyncSession, days: int = 7) -> int:
    """Find and create associations between semantically similar items."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(Item)
        .where(Item.embedding.isnot(None))
        .where(Item.created_at > since)
    )
    result = await db.execute(stmt)
    recent_items = result.scalars().all()

    created = 0
    for item in recent_items:
        similar = await find_similar_items(db, item, limit=3)
        for similar_item, distance in similar:
            similarity = 1 - distance
            if similarity < 0.85:
                continue

            # Check if association already exists
            existing = await db.execute(
                select(Association).where(
                    ((Association.item_a_id == item.id) & (Association.item_b_id == similar_item.id))
                    | ((Association.item_a_id == similar_item.id) & (Association.item_b_id == item.id))
                )
            )
            if existing.scalar_one_or_none():
                continue

            assoc = Association(
                item_a_id=item.id,
                item_b_id=similar_item.id,
                association_type=AssociationType.similar,
                strength=similarity,
                source=AssociationSource.ai,
            )
            db.add(assoc)
            created += 1

    if created:
        await db.commit()
        logger.info(f"Discovered {created} new associations")

    return created


async def run_learning_sweep():
    """Daily learning sweep — runs all learning tasks.

    Called by the worker on a schedule.
    """
    async with async_session() as db:
        logger.info("Starting daily learning sweep...")

        # 1. Discover associations
        assoc_count = await discover_associations(db)
        logger.info(f"Association discovery: {assoc_count} new")

        # 2. Memory maintenance
        await maintain_memories(db)

        # 3. Build and log behavioral model
        model = await get_behavioral_model(db)
        logger.info(f"Behavioral model: {json.dumps(model, default=str)}")

        logger.info("Learning sweep complete")


async def maintain_memories(db: AsyncSession):
    """Memory maintenance: decay old memories, dedup similar ones."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # Decay confidence for unused memories
    stmt = (
        select(MemoryFact)
        .where(MemoryFact.confidence > 0.1)
        .where(
            (MemoryFact.last_accessed.is_(None))
            | (MemoryFact.last_accessed < thirty_days_ago)
        )
    )
    result = await db.execute(stmt)
    decayed = 0
    for memory in result.scalars():
        memory.confidence *= 0.9  # 10% decay
        decayed += 1

    # Delete very low confidence memories
    stmt = select(MemoryFact).where(MemoryFact.confidence <= 0.1)
    result = await db.execute(stmt)
    deleted = 0
    for memory in result.scalars():
        await db.delete(memory)
        deleted += 1

    if decayed or deleted:
        await db.commit()
        logger.info(f"Memory maintenance: {decayed} decayed, {deleted} deleted")

    # Dedup similar memories (embedding similarity > 0.95)
    stmt = select(MemoryFact).where(MemoryFact.embedding.isnot(None)).order_by(MemoryFact.created_at)
    result = await db.execute(stmt)
    all_memories = result.scalars().all()

    merged = 0
    seen_ids = set()
    for i, mem_a in enumerate(all_memories):
        if mem_a.id in seen_ids:
            continue
        for mem_b in all_memories[i + 1:]:
            if mem_b.id in seen_ids:
                continue
            # Compute similarity
            distance = sum(
                (a - b) ** 2 for a, b in zip(mem_a.embedding[:50], mem_b.embedding[:50])
            ) ** 0.5
            # Rough check using first 50 dims — actual cosine would be better but this is cheaper
            if distance < 0.1:  # very similar
                # Keep the one with higher confidence
                if mem_a.confidence >= mem_b.confidence:
                    await db.delete(mem_b)
                    seen_ids.add(mem_b.id)
                else:
                    await db.delete(mem_a)
                    seen_ids.add(mem_a.id)
                merged += 1

    if merged:
        await db.commit()
        logger.info(f"Memory dedup: {merged} merged")
