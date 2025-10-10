"""Interaction model for tracking user behavior and learning."""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class Interaction(Base):
    """Interaction table for logging user interactions for learning."""
    
    __tablename__ = "interactions"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(BigInteger, ForeignKey("items.id"), nullable=True, index=True)
    
    # Interaction type
    interaction_type = Column(String, nullable=False, index=True)
    # Types: complete, snooze, dismiss, edit, search, helpful, not_helpful
    
    # Context
    context = Column(JSON, default=dict)  # Additional context about the interaction
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<Interaction(type={self.interaction_type}, user_id={self.user_id}, item_id={self.item_id})>"

