"""Calendar event model for caching calendar data."""
from sqlalchemy import Column, BigInteger, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class CalendarEvent(Base):
    """Calendar event table for caching calendar data."""
    
    __tablename__ = "calendar_events"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Event identification
    external_id = Column(String, nullable=False)  # ID from Google/CalDAV
    source = Column(String, nullable=False)  # google, caldav
    
    # Event details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    
    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    all_day = Column(Boolean, default=False)
    
    # Status
    status = Column(String, default="confirmed")  # confirmed, tentative, cancelled
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<CalendarEvent(title='{self.title}', start={self.start_time})>"

