"""Items CRUD + quick capture endpoint."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.item import Item, ItemStatus, ItemType, EnrichmentStatus
from app.models.item_tag import ItemTag
from app.models.tag import Tag
from app.models.interaction import Interaction, InteractionType
from app.schemas.item import ItemCapture, ItemUpdate, ItemResponse, ItemListResponse, TagResponse
from app.services.capture_service import quick_capture

router = APIRouter(prefix="/api/items", tags=["items"])


def _build_item_response(item: Item) -> ItemResponse:
    tags = []
    if item.item_tags:
        for it in item.item_tags:
            tags.append(TagResponse(
                id=it.tag.id,
                name=it.tag.name,
                source=it.source.value,
                confidence=it.confidence,
            ))
    return ItemResponse(
        id=item.id,
        content=item.content,
        parsed_title=item.parsed_title,
        item_type=item.item_type.value if item.item_type else None,
        status=item.status.value,
        enrichment_status=item.enrichment_status.value,
        priority=item.priority,
        due_date=item.due_date,
        completed_at=item.completed_at,
        parent_id=item.parent_id,
        ai_confidence=item.ai_confidence,
        tags=tags,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/capture", response_model=ItemResponse, status_code=201)
async def capture_item(
    body: ItemCapture,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Phase 1: Quick capture. Returns immediately, enrichment happens async."""
    from app.workers.enrichment import enqueue_enrichment

    item = await quick_capture(db, body.content, body.tags)
    await enqueue_enrichment(str(item.id))
    await db.refresh(item, attribute_names=["item_tags"])
    return _build_item_response(item)


@router.get("", response_model=ItemListResponse)
async def list_items(
    status: str | None = Query(None),
    item_type: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    stmt = (
        select(Item)
        .options(selectinload(Item.item_tags).selectinload(ItemTag.tag))
        .order_by(Item.created_at.desc())
    )

    if status:
        stmt = stmt.where(Item.status == ItemStatus(status))
    if item_type:
        stmt = stmt.where(Item.item_type == ItemType(item_type))
    if tag:
        stmt = stmt.join(Item.item_tags).join(ItemTag.tag).where(Tag.name == tag)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().unique().all()

    return ItemListResponse(
        items=[_build_item_response(i) for i in items],
        total=total,
    )


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    stmt = (
        select(Item)
        .options(selectinload(Item.item_tags).selectinload(ItemTag.tag))
        .where(Item.id == item_id)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _build_item_response(item)


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: UUID,
    body: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    stmt = (
        select(Item)
        .options(selectinload(Item.item_tags).selectinload(ItemTag.tag))
        .where(Item.id == item_id)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = body.model_dump(exclude_unset=True)

    # Track classification corrections
    if "item_type" in update_data and update_data["item_type"] != (item.item_type.value if item.item_type else None):
        interaction = Interaction(
            item_id=item.id,
            interaction_type=InteractionType.classification_corrected,
            context={"old": item.item_type.value if item.item_type else None, "new": update_data["item_type"]},
        )
        db.add(interaction)

    # Handle completion
    if update_data.get("status") == "done" and item.status != ItemStatus.done:
        update_data["completed_at"] = datetime.now(timezone.utc)
        interaction = Interaction(
            item_id=item.id,
            interaction_type=InteractionType.complete,
        )
        db.add(interaction)

    for key, value in update_data.items():
        if key == "item_type" and value:
            setattr(item, key, ItemType(value))
        elif key == "status" and value:
            setattr(item, key, ItemStatus(value))
        else:
            setattr(item, key, value)

    await db.commit()
    await db.refresh(item, attribute_names=["item_tags"])
    return _build_item_response(item)


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    interaction = Interaction(item_id=item.id, interaction_type=InteractionType.delete)
    db.add(interaction)

    item.status = ItemStatus.archived
    await db.commit()
