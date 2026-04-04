import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssociationType(str, enum.Enum):
    similar = "similar"
    subtask = "subtask"
    related = "related"
    blocks = "blocks"
    followup = "followup"


class AssociationSource(str, enum.Enum):
    ai = "ai"
    user = "user"


class Association(Base):
    __tablename__ = "associations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=False
    )
    item_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=False
    )
    association_type: Mapped[AssociationType] = mapped_column(Enum(AssociationType))
    strength: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[AssociationSource] = mapped_column(Enum(AssociationSource), default=AssociationSource.ai)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
