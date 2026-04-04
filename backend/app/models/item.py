import enum
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, Enum, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base


class ItemType(str, enum.Enum):
    task = "task"
    idea = "idea"
    note = "note"
    event = "event"
    reference = "reference"


class ItemStatus(str, enum.Enum):
    inbox = "inbox"
    active = "active"
    done = "done"
    cancelled = "cancelled"
    archived = "archived"


class EnrichmentStatus(str, enum.Enum):
    pending = "pending"
    complete = "complete"
    failed = "failed"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_title: Mapped[str | None] = mapped_column(String(500))
    item_type: Mapped[ItemType | None] = mapped_column(Enum(ItemType))
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.inbox)
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        Enum(EnrichmentStatus), default=EnrichmentStatus.pending
    )
    priority: Mapped[str | None] = mapped_column(String(20))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=True
    )
    embedding: Mapped[list | None] = mapped_column(Vector(settings.embedding_dimensions))
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    ai_metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    item_tags = relationship("ItemTag", back_populates="item", cascade="all, delete-orphan")
    children = relationship("Item", back_populates="parent", remote_side="Item.id")
    parent = relationship("Item", back_populates="children", remote_side=[parent_id])

    __table_args__ = (
        Index("idx_items_status", "status"),
        Index("idx_items_type", "item_type"),
        Index("idx_items_created", "created_at"),
        Index("idx_items_enrichment", "enrichment_status"),
    )
