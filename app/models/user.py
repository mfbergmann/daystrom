"""User model."""
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User table for storing user preferences and settings."""
    
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # User preferences
    timezone = Column(String, default="UTC")
    digest_enabled = Column(Boolean, default=True)
    digest_time = Column(String, default="08:00")
    weekly_digest_enabled = Column(Boolean, default=True)
    weekly_digest_time = Column(String, default="09:00")
    
    # Calendar integration flags
    google_calendar_enabled = Column(Boolean, default=False)
    google_calendar_refresh_token = Column(String, nullable=True)
    caldav_enabled = Column(Boolean, default=False)
    
    # Learning and adaptation
    interaction_patterns = Column(JSON, default=dict)
    preferences = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.telegram_username})>"

