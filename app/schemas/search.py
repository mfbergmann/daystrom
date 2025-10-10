"""Pydantic schemas for search operations."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SearchQuery(BaseModel):
    """Schema for search query."""
    query: str
    limit: int = 10
    threshold: float = 0.7


class SearchResult(BaseModel):
    """Schema for search result."""
    item_id: int
    content: str
    item_type: Optional[str] = None
    similarity: float
    created_at: datetime
    tags: List[str] = []
    
    class Config:
        from_attributes = True

