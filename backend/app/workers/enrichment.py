"""Phase 2 enrichment pipeline — runs asynchronously via ARQ worker."""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.item import Item, EnrichmentStatus, ItemType
from app.models.tag import Tag
from app.models.item_tag import ItemTag, TagSource
from app.services.classifier import classify_item
from app.services.embedding_service import embed_text, find_similar_items
from app.services.memory_service import extract_memories
from app.services.context_service import assemble_classification_context
from app.models.association import Association, AssociationType, AssociationSource
from app.routers.events import publish_event

logger = logging.getLogger(__name__)


async def enqueue_enrichment(item_id: str):
    """Enqueue an enrichment job to Redis/ARQ."""
    import redis.asyncio as aioredis
    from app.core.config import settings

    r = aioredis.from_url(settings.redis_url)
    try:
        await r.rpush("arq:queue", json.dumps({"function": "enrich_item", "args": [item_id]}))
    finally:
        await r.close()


async def enrich_item(ctx: dict, item_id: str):
    """Full enrichment pipeline for a captured item.

    1. Classify with LLM (type, tags, priority, dates)
    2. Generate embedding
    3. Apply tags
    4. Find similar items
    5. Extract memories
    6. Push SSE update
    """
    async with async_session() as db:
        result = await db.execute(select(Item).where(Item.id == UUID(item_id)))
        item = result.scalar_one_or_none()
        if not item:
            logger.error(f"Item {item_id} not found for enrichment")
            return

        try:
            # Build rich context from memories + corrections + tags
            context = await assemble_classification_context(db, item.content)

            # 1. Classify
            classification = await classify_item(item.content, context=context)
            logger.info(f"Classified item {item_id}: {classification.get('item_type')} (confidence: {classification.get('confidence')})")

            item.item_type = ItemType(classification.get("item_type", "note"))
            item.parsed_title = classification.get("parsed_title", item.content[:80])
            item.ai_confidence = classification.get("confidence", 0.5)
            item.priority = classification.get("priority")

            if classification.get("due_date") and not item.due_date:
                try:
                    item.due_date = datetime.fromisoformat(classification["due_date"])
                except (ValueError, TypeError):
                    pass

            item.ai_metadata = {
                "is_actionable_by_agent": classification.get("is_actionable_by_agent", False),
                "raw_classification": classification,
            }

            # 2. Generate embedding
            embedding = await embed_text(item.content)
            item.embedding = embedding

            # 3. Apply AI-suggested tags
            ai_tags = classification.get("tags", [])
            for tag_name in ai_tags:
                tag_name = tag_name.strip().lower()
                if not tag_name:
                    continue

                tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
                tag = tag_result.scalar_one_or_none()
                if not tag:
                    tag = Tag(name=tag_name, auto_generated=True)
                    db.add(tag)
                    await db.flush()

                # Check if tag already exists on item (user may have pre-tagged)
                existing = await db.execute(
                    select(ItemTag).where(ItemTag.item_id == item.id, ItemTag.tag_id == tag.id)
                )
                if not existing.scalar_one_or_none():
                    item_tag = ItemTag(
                        item_id=item.id,
                        tag_id=tag.id,
                        source=TagSource.ai,
                        confidence=classification.get("confidence", 0.5),
                    )
                    db.add(item_tag)

                tag.usage_count += 1
                tag.last_used_at = datetime.now(timezone.utc)

            # 4. Mark enrichment complete
            item.enrichment_status = EnrichmentStatus.complete
            await db.commit()

            # 5. Extract memories (non-blocking, errors don't fail enrichment)
            try:
                await extract_memories(db, item.content, item.id)
            except Exception as e:
                logger.warning(f"Memory extraction failed for {item_id}: {e}")

            # 6. Discover associations with existing items
            try:
                similar = await find_similar_items(db, item, limit=3)
                for similar_item, distance in similar:
                    similarity = 1 - distance
                    if similarity >= 0.7:
                        assoc = Association(
                            item_a_id=item.id,
                            item_b_id=similar_item.id,
                            association_type=AssociationType.similar,
                            strength=similarity,
                            source=AssociationSource.ai,
                        )
                        db.add(assoc)
                await db.commit()
            except Exception as e:
                logger.warning(f"Association discovery failed for {item_id}: {e}")

            # 7. Auto-spawn agent task if item is actionable
            if item.ai_metadata and item.ai_metadata.get("is_actionable_by_agent"):
                try:
                    from app.services.agent_service import detect_agent_task_type, create_agent_task
                    task_type = detect_agent_task_type(item.content, item.ai_metadata)
                    if task_type:
                        await create_agent_task(db, item.id, item.content, task_type)
                        logger.info(f"Spawned agent task for item {item_id}: {task_type.value}")
                except Exception as e:
                    logger.warning(f"Agent task creation failed for {item_id}: {e}")

            # 8. Push SSE event
            await publish_event("item_enriched", {
                "item_id": item_id,
                "item_type": item.item_type.value if item.item_type else None,
                "parsed_title": item.parsed_title,
                "ai_confidence": item.ai_confidence,
                "tags": ai_tags,
            })

            logger.info(f"Enrichment complete for item {item_id}")

        except Exception as e:
            logger.error(f"Enrichment failed for item {item_id}: {e}")
            item.enrichment_status = EnrichmentStatus.failed
            await db.commit()
            raise
