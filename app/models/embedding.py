"""Embedding model for vector search."""
from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base


class Embedding(Base):
    """Embedding table for storing vector embeddings."""
    
    __tablename__ = "embeddings"
    
    id = Column(BigInteger, primary_key=True, index=True)
    item_id = Column(BigInteger, ForeignKey("items.id"), nullable=False, unique=True, index=True)
    
    # Vector embedding (text-embedding-3-large uses 3072 dimensions)
    embedding = Column(Vector(3072), nullable=False)
    
    # Relationships
    item = relationship("Item", back_populates="embedding")
    
    def __repr__(self):
        return f"<Embedding(item_id={self.item_id})>"

