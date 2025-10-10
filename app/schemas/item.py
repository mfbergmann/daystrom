"""Pydantic schemas for Item model."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ItemType(str, Enum):
    """Types of items."""
    IDEA = "idea"
    TASK = "task"
    EVENT = "event"
    REFERENCE = "reference"
    NOTE = "note"


class ItemCreate(BaseModel):
    """Schema for creating a new item."""
    content: str
    original_content: Optional[str] = None
    item_type: Optional[ItemType] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    counterparties: List[str] = Field(default_factory=list)
    media_type: Optional[str] = None
    media_file_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ItemUpdate(BaseModel):
    """Schema for updating an existing item."""
    content: Optional[str] = None
    item_type: Optional[ItemType] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    counterparties: Optional[List[str]] = None
    completed: Optional[str] = None
    metadata: Optional[dict] = None


class ItemResponse(BaseModel):
    """Schema for item response."""
    id: int
    user_id: int
    content: str
    original_content: Optional[str] = None
    item_type: Optional[ItemType] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    counterparties: List[str] = Field(default_factory=list)
    media_type: Optional[str] = None
    completed: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

