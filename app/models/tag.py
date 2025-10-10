"""Tag model for organizing and categorizing items."""
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Tag(Base):
    """Tag table for extracted tags and their usage statistics."""
    
    __tablename__ = "tags"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Tag information
    name = Column(String, nullable=False, index=True)
    tag_type = Column(String, default="general")  # general, person, project, etc.
    
    # Usage statistics
    usage_count = Column(Integer, default=1)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uix_user_tag'),
    )
    
    def __repr__(self):
        return f"<Tag(name='{self.name}', type={self.tag_type}, usage={self.usage_count})>"

