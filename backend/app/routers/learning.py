"""Learning & behavioral model endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.interaction import Interaction, InteractionType
from app.models.association import Association
from app.models.item import Item
from app.services.learning_service import get_behavioral_model

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/model")
async def behavioral_model(
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Get the current behavioral model — how the system understands you."""
    return await get_behavioral_model(db)


@router.get("/interactions")
async def recent_interactions(
    interaction_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    stmt = select(Interaction).order_by(Interaction.created_at.desc()).limit(limit)
    if interaction_type:
        stmt = stmt.where(Interaction.interaction_type == InteractionType(interaction_type))

    result = await db.execute(stmt)
    return [
        {
            "id": str(i.id),
            "item_id": str(i.item_id) if i.item_id else None,
            "type": i.interaction_type.value,
            "context": i.context,
            "created_at": i.created_at.isoformat(),
        }
        for i in result.scalars()
    ]


@router.get("/associations/{item_id}")
async def item_associations(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Get items associated with a given item."""
    stmt = select(Association).where(
        (Association.item_a_id == item_id) | (Association.item_b_id == item_id)
    ).order_by(Association.strength.desc())

    result = await db.execute(stmt)
    associations = result.scalars().all()

    items = []
    for assoc in associations:
        other_id = assoc.item_b_id if assoc.item_a_id == item_id else assoc.item_a_id
        item_result = await db.execute(select(Item).where(Item.id == other_id))
        other_item = item_result.scalar_one_or_none()
        if other_item:
            items.append({
                "id": str(other_item.id),
                "content": other_item.content,
                "parsed_title": other_item.parsed_title,
                "item_type": other_item.item_type.value if other_item.item_type else None,
                "association_type": assoc.association_type.value,
                "strength": round(assoc.strength, 3),
                "source": assoc.source.value,
            })

    return items
