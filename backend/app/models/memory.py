import enum
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, Enum, Float, Integer, DateTime, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class MemoryType(str, enum.Enum):
    fact = "fact"
    preference = "preference"
    pattern = "pattern"
    association = "association"
    context = "context"


class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(Enum(MemoryType), default=MemoryType.fact)
    embedding: Mapped[list | None] = mapped_column(Vector(settings.embedding_dimensions))
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_item_ids: Mapped[dict | None] = mapped_column(JSON)  # list of UUIDs
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
