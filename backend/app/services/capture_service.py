"""Two-phase capture pipeline.

Phase 1 (sync, <100ms): Store raw item, return ID.
Phase 2 (async, worker): Classify, embed, tag, discover associations.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item, ItemStatus, EnrichmentStatus
from app.models.tag import Tag
from app.models.item_tag import ItemTag, TagSource
from app.services.classifier import heuristic_preparse

logger = logging.getLogger(__name__)


async def quick_capture(db: AsyncSession, content: str, user_tags: list[str] | None = None) -> Item:
    """Phase 1: Fast synchronous capture. Stores the item immediately.

    Returns the item with basic heuristic hints applied.
    """
    hints = heuristic_preparse(content)

    item = Item(
        content=content,
        parsed_title=content[:80] if len(content) <= 80 else content[:77] + "...",
        item_type=hints.get("type_hint"),
        status=ItemStatus.inbox,
        enrichment_status=EnrichmentStatus.pending,
        priority=hints.get("priority_hint"),
    )

    # Parse heuristic due date hint
    due_hint = hints.get("due_date_hint")
    if due_hint:
        try:
            item.due_date = datetime.fromisoformat(due_hint)
        except ValueError:
            pass

    db.add(item)
    await db.flush()

    # Apply any user-specified tags immediately
    if user_tags:
        for tag_name in user_tags:
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue
            # Get or create tag
            result = await db.execute(select(Tag).where(Tag.name == tag_name))
            tag = result.scalar_one_or_none()
            if not tag:
                tag = Tag(name=tag_name, auto_generated=False)
                db.add(tag)
                await db.flush()

            item_tag = ItemTag(item_id=item.id, tag_id=tag.id, source=TagSource.user, confidence=1.0)
            db.add(item_tag)

    await db.commit()
    await db.refresh(item)

    logger.info(f"Captured item {item.id}: {content[:50]}...")
    return item
