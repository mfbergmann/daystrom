"""Context assembler — builds rich context for LLM calls.

Assembles system prompt + memories + recent items + corrections
into a coherent context window for any LLM interaction.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.memory import MemoryFact
from app.models.tag import Tag
from app.services.memory_service import retrieve_relevant_memories
from app.services.learning_service import get_classification_corrections, compute_tag_affinity

logger = logging.getLogger(__name__)

PERSONA = """You are Daystrom, an intelligent personal assistant for task and idea management.
You help the user capture, organize, and act on their thoughts.
You are warm but efficient. You learn from the user's patterns and adapt over time.
You speak concisely and naturally."""


async def assemble_context(
    db: AsyncSession,
    query: str,
    include_corrections: bool = False,
    include_recent: bool = True,
    memory_limit: int = 8,
    recent_limit: int = 10,
) -> list[dict]:
    """Assemble a context window for an LLM call.

    Returns a list of message dicts ready for chat_completion.
    """
    messages = [{"role": "system", "content": PERSONA}]

    # 1. Top tags for context
    stmt = select(Tag.name).where(Tag.merged_into_id.is_(None)).order_by(Tag.usage_count.desc()).limit(20)
    result = await db.execute(stmt)
    top_tags = [row[0] for row in result]
    if top_tags:
        messages.append({
            "role": "system",
            "content": f"The user's most-used tags: {', '.join(top_tags)}",
        })

    # 2. Relevant memory facts
    try:
        memories = await retrieve_relevant_memories(db, query, limit=memory_limit)
        if memories:
            lines = ["Things I remember about the user:"]
            for mem in memories:
                lines.append(f"- [{mem.memory_type.value}] {mem.content}")
            messages.append({"role": "system", "content": "\n".join(lines)})
    except Exception as e:
        logger.warning(f"Failed to retrieve memories: {e}")

    # 3. Classification corrections as few-shot examples
    if include_corrections:
        try:
            corrections = await get_classification_corrections(db, days=30)
            if corrections:
                lines = ["Recent corrections the user made to my classifications:"]
                for c in corrections[:5]:
                    lines.append(
                        f"- \"{c['content'][:100]}\" was {c['was_classified_as']}, "
                        f"user corrected to {c['corrected_to']}"
                    )
                messages.append({"role": "system", "content": "\n".join(lines)})
        except Exception as e:
            logger.warning(f"Failed to get corrections: {e}")

    # 4. Recent items for temporal context
    if include_recent:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        stmt = (
            select(Item)
            .where(Item.created_at > since)
            .order_by(Item.created_at.desc())
            .limit(recent_limit)
        )
        result = await db.execute(stmt)
        recent = result.scalars().all()
        if recent:
            lines = ["Recent items (last 24h):"]
            for item in recent:
                type_str = item.item_type.value if item.item_type else "?"
                status_str = item.status.value
                lines.append(f"- [{type_str}/{status_str}] {item.content[:100]}")
            messages.append({"role": "system", "content": "\n".join(lines)})

    return messages


async def assemble_classification_context(db: AsyncSession, content: str) -> str:
    """Build a compact context string specifically for classification calls."""
    parts = []

    # Top tags
    stmt = select(Tag.name).where(Tag.merged_into_id.is_(None)).order_by(Tag.usage_count.desc()).limit(20)
    result = await db.execute(stmt)
    top_tags = [row[0] for row in result]
    if top_tags:
        parts.append(f"User's common tags: {', '.join(top_tags)}")

    # Recent corrections
    try:
        corrections = await get_classification_corrections(db, days=30)
        if corrections:
            lines = ["Recent corrections:"]
            for c in corrections[:5]:
                lines.append(
                    f"- \"{c['content'][:80]}\" was {c['was_classified_as']}, "
                    f"corrected to {c['corrected_to']}"
                )
            parts.append("\n".join(lines))
    except Exception:
        pass

    # Relevant memories
    try:
        memories = await retrieve_relevant_memories(db, content, limit=5)
        if memories:
            lines = ["Relevant context:"]
            for mem in memories:
                lines.append(f"- {mem.content}")
            parts.append("\n".join(lines))
    except Exception:
        pass

    return "\n\n".join(parts)
