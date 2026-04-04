"""Search endpoint — hybrid semantic + full-text search."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.interaction import Interaction, InteractionType
from app.services.embedding_service import hybrid_search

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResult(BaseModel):
    id: UUID
    content: str
    parsed_title: str | None = None
    item_type: str | None = None
    status: str
    score: float
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SearchResult])
async def search_items(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    # Track search interaction
    interaction = Interaction(
        interaction_type=InteractionType.search,
        context={"query": q},
    )
    db.add(interaction)
    await db.commit()

    results = await hybrid_search(db, q, limit=limit)
    return [
        SearchResult(
            id=item.id,
            content=item.content,
            parsed_title=item.parsed_title,
            item_type=item.item_type.value if item.item_type else None,
            status=item.status.value,
            score=round(score, 3),
            created_at=item.created_at.isoformat(),
        )
        for item, score in results
    ]
