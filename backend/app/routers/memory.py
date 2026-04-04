"""Memory facts inspection and management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.memory import MemoryFact, MemoryType
from app.models.interaction import Interaction, InteractionType

router = APIRouter(prefix="/api/memories", tags=["memories"])


class MemoryResponse(BaseModel):
    id: UUID
    content: str
    memory_type: str
    confidence: float
    access_count: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MemoryUpdate(BaseModel):
    content: str | None = None
    memory_type: str | None = None
    confidence: float | None = None


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    memory_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    stmt = (
        select(MemoryFact)
        .where(MemoryFact.confidence > 0.1)
        .order_by(MemoryFact.confidence.desc(), MemoryFact.access_count.desc())
        .limit(limit)
    )
    if memory_type:
        stmt = stmt.where(MemoryFact.memory_type == MemoryType(memory_type))

    result = await db.execute(stmt)
    return [
        MemoryResponse(
            id=m.id,
            content=m.content,
            memory_type=m.memory_type.value,
            confidence=round(m.confidence, 2),
            access_count=m.access_count,
            created_at=m.created_at.isoformat(),
            updated_at=m.updated_at.isoformat(),
        )
        for m in result.scalars()
    ]


@router.get("/stats")
async def memory_stats(
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    total = await db.scalar(
        select(func.count(MemoryFact.id)).where(MemoryFact.confidence > 0.1)
    ) or 0
    by_type = {}
    stmt = (
        select(MemoryFact.memory_type, func.count(MemoryFact.id))
        .where(MemoryFact.confidence > 0.1)
        .group_by(MemoryFact.memory_type)
    )
    result = await db.execute(stmt)
    for row in result:
        by_type[row[0].value if row[0] else "unknown"] = row[1]

    avg_confidence = await db.scalar(
        select(func.avg(MemoryFact.confidence)).where(MemoryFact.confidence > 0.1)
    )

    return {
        "total": total,
        "by_type": by_type,
        "avg_confidence": round(float(avg_confidence), 2) if avg_confidence else 0,
    }


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    body: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    result = await db.execute(select(MemoryFact).where(MemoryFact.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    interaction = Interaction(
        interaction_type=InteractionType.fact_confirmed,
        context={"memory_id": str(memory_id), "action": "edit"},
    )
    db.add(interaction)

    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "memory_type" and value:
            setattr(memory, key, MemoryType(value))
        else:
            setattr(memory, key, value)

    await db.commit()
    await db.refresh(memory)
    return MemoryResponse(
        id=memory.id, content=memory.content, memory_type=memory.memory_type.value,
        confidence=round(memory.confidence, 2), access_count=memory.access_count,
        created_at=memory.created_at.isoformat(), updated_at=memory.updated_at.isoformat(),
    )


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    result = await db.execute(select(MemoryFact).where(MemoryFact.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    interaction = Interaction(
        interaction_type=InteractionType.fact_deleted,
        context={"memory_id": str(memory_id), "content": memory.content[:200]},
    )
    db.add(interaction)

    await db.delete(memory)
    await db.commit()
