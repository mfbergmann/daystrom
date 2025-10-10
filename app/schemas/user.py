"""Pydantic schemas for User model."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    telegram_id: int
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating user settings."""
    timezone: Optional[str] = None
    digest_enabled: Optional[bool] = None
    digest_time: Optional[str] = None
    weekly_digest_enabled: Optional[bool] = None
    weekly_digest_time: Optional[str] = None
    preferences: Optional[dict] = None


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    telegram_id: int
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timezone: str
    digest_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

