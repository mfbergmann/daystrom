import enum
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Enum, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base


class TagType(str, enum.Enum):
    category = "category"
    person = "person"
    project = "project"
    location = "location"
    auto = "auto"


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    tag_type: Mapped[TagType] = mapped_column(Enum(TagType), default=TagType.auto)
    color: Mapped[str | None] = mapped_column(String(7))
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list | None] = mapped_column(Vector(settings.embedding_dimensions))
    parent_tag_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), nullable=True
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), nullable=True
    )
    auto_generated: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    item_tags = relationship("ItemTag", back_populates="tag")

    __table_args__ = (Index("idx_tags_name", "name"),)
