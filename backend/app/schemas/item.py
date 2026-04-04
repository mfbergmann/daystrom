from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ItemCapture(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    tags: list[str] | None = None  # optional user-specified tags


class ItemUpdate(BaseModel):
    content: str | None = None
    parsed_title: str | None = None
    item_type: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None


class TagResponse(BaseModel):
    id: UUID
    name: str
    source: str
    confidence: float | None = None

    model_config = {"from_attributes": True}


class ItemResponse(BaseModel):
    id: UUID
    content: str
    parsed_title: str | None = None
    item_type: str | None = None
    status: str
    enrichment_status: str
    priority: str | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    parent_id: UUID | None = None
    ai_confidence: float | None = None
    tags: list[TagResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
