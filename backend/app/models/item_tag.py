import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TagSource(str, enum.Enum):
    ai = "ai"
    user = "user"


class ItemTag(Base):
    __tablename__ = "item_tags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("items.id"), nullable=False)
    tag_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tags.id"), nullable=False)
    source: Mapped[TagSource] = mapped_column(Enum(TagSource), default=TagSource.ai)
    confidence: Mapped[float | None] = mapped_column(Float)

    item = relationship("Item", back_populates="item_tags")
    tag = relationship("Tag", back_populates="item_tags")

    __table_args__ = (UniqueConstraint("item_id", "tag_id", name="uq_item_tag"),)
