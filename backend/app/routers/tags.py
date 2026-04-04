"""Tag management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.tag import Tag
from app.models.item_tag import ItemTag

router = APIRouter(prefix="/api/tags", tags=["tags"])


class TagResponse(BaseModel):
    id: UUID
    name: str
    tag_type: str
    color: str | None = None
    usage_count: int
    auto_generated: bool

    model_config = {"from_attributes": True}


class TagUpdate(BaseModel):
    name: str | None = None
    tag_type: str | None = None
    color: str | None = None


class TagMerge(BaseModel):
    source_ids: list[UUID]
    target_id: UUID


@router.get("", response_model=list[TagResponse])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    stmt = select(Tag).where(Tag.merged_into_id.is_(None)).order_by(Tag.usage_count.desc())
    result = await db.execute(stmt)
    tags = result.scalars().all()
    return [
        TagResponse(
            id=t.id,
            name=t.name,
            tag_type=t.tag_type.value,
            color=t.color,
            usage_count=t.usage_count,
            auto_generated=t.auto_generated,
        )
        for t in tags
    ]


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID,
    body: TagUpdate,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(tag, key, value)

    await db.commit()
    await db.refresh(tag)
    return TagResponse(
        id=tag.id, name=tag.name, tag_type=tag.tag_type.value,
        color=tag.color, usage_count=tag.usage_count, auto_generated=tag.auto_generated,
    )


@router.post("/merge", status_code=200)
async def merge_tags(
    body: TagMerge,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Merge multiple tags into a target tag."""
    result = await db.execute(select(Tag).where(Tag.id == body.target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target tag not found")

    for source_id in body.source_ids:
        if source_id == body.target_id:
            continue
        # Reassign all item_tags
        stmt = select(ItemTag).where(ItemTag.tag_id == source_id)
        result = await db.execute(stmt)
        item_tags = result.scalars().all()
        for it in item_tags:
            it.tag_id = body.target_id

        # Mark source as merged
        source_result = await db.execute(select(Tag).where(Tag.id == source_id))
        source = source_result.scalar_one_or_none()
        if source:
            source.merged_into_id = body.target_id

    await db.commit()
    return {"merged": len(body.source_ids), "into": str(body.target_id)}
