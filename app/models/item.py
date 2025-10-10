"""Item model for capturing thoughts, tasks, and ideas."""
from sqlalchemy import Column, BigInteger, String, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class ItemType(str, enum.Enum):
    """Types of items that can be captured."""
    IDEA = "idea"
    TASK = "task"
    EVENT = "event"
    REFERENCE = "reference"
    NOTE = "note"


class Item(Base):
    """Item table for storing captured thoughts and information."""
    
    __tablename__ = "items"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    original_content = Column(Text, nullable=True)  # For voice/image transcriptions
    item_type = Column(SQLEnum(ItemType), nullable=True, index=True)
    
    # Extracted information
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    priority = Column(String, nullable=True)  # low, medium, high
    tags = Column(JSON, default=list)  # List of extracted tags
    counterparties = Column(JSON, default=list)  # People mentioned
    
    # Media references
    media_type = Column(String, nullable=True)  # voice, photo, text
    media_file_id = Column(String, nullable=True)
    
    # Status
    completed = Column(SQLEnum(enum.Enum("ItemStatus", "pending active completed cancelled")), 
                       default="pending", index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    embedding = relationship("Embedding", back_populates="item", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Item(id={self.id}, type={self.item_type}, content='{self.content[:50]}...')>"

