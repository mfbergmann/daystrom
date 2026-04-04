"""Memory service for persistent AI memory facts."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.memory import MemoryFact, MemoryType
from app.services.ai_service import chat_completion, generate_embedding

logger = logging.getLogger(__name__)

MEMORY_EXTRACTION_PROMPT = """You are analyzing a user's item to extract durable facts worth remembering.
Given this item content, extract any facts about the user's preferences, habits, relationships,
projects, or context that would be useful to remember across sessions.

Respond with a JSON array of objects, each with:
- "content": the fact in natural language
- "memory_type": one of "fact", "preference", "pattern", "association", "context"

If there are no facts worth extracting, respond with an empty array: []

Example output:
[{"content": "User is working on a kitchen renovation project", "memory_type": "context"},
 {"content": "User prefers morning meetings", "memory_type": "preference"}]"""


async def extract_memories(db: AsyncSession, item_content: str, item_id: UUID) -> list[MemoryFact]:
    """Extract memory-worthy facts from an item's content."""
    import json

    try:
        response = await chat_completion([
            {"role": "system", "content": MEMORY_EXTRACTION_PROMPT},
            {"role": "user", "content": item_content},
        ])
        content = response.get("message", {}).get("content", "[]")

        # Parse JSON from response
        try:
            facts_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```" in content:
                json_str = content.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                facts_data = json.loads(json_str.strip())
            else:
                return []

        if not isinstance(facts_data, list):
            return []

        created = []
        for fact_data in facts_data:
            fact_content = fact_data.get("content", "")
            if not fact_content:
                continue

            embedding = await generate_embedding(fact_content)
            fact = MemoryFact(
                content=fact_content,
                memory_type=MemoryType(fact_data.get("memory_type", "fact")),
                embedding=embedding,
                source_item_ids=[str(item_id)],
            )
            db.add(fact)
            created.append(fact)

        if created:
            await db.commit()
            logger.info(f"Extracted {len(created)} memory facts from item {item_id}")

        return created

    except Exception as e:
        logger.error(f"Memory extraction failed: {e}")
        return []


async def retrieve_relevant_memories(
    db: AsyncSession, query: str, limit: int = 10
) -> list[MemoryFact]:
    """Retrieve memories relevant to a query, ordered by similarity."""
    query_embedding = await generate_embedding(query)

    distance_expr = MemoryFact.embedding.cosine_distance(query_embedding)
    stmt = (
        select(MemoryFact)
        .where(MemoryFact.embedding.isnot(None))
        .where(MemoryFact.confidence > 0.1)
        .order_by(distance_expr)
        .limit(limit)
    )

    result = await db.execute(stmt)
    memories = result.scalars().all()

    # Update access tracking
    now = datetime.now(timezone.utc)
    for mem in memories:
        mem.access_count += 1
        mem.last_accessed = now
    await db.commit()

    return memories


async def build_context_block(db: AsyncSession, query: str) -> str:
    """Build a context string from relevant memories for LLM calls."""
    memories = await retrieve_relevant_memories(db, query, limit=8)
    if not memories:
        return ""

    lines = ["Here are relevant things I remember about the user:"]
    for mem in memories:
        lines.append(f"- [{mem.memory_type.value}] {mem.content}")

    return "\n".join(lines)
