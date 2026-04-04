import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InteractionType(str, enum.Enum):
    complete = "complete"
    snooze = "snooze"
    edit = "edit"
    delete = "delete"
    search = "search"
    tag_accepted = "tag_accepted"
    tag_rejected = "tag_rejected"
    classification_corrected = "classification_corrected"
    fact_confirmed = "fact_confirmed"
    fact_deleted = "fact_deleted"
    chat = "chat"


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("items.id"), nullable=True
    )
    interaction_type: Mapped[InteractionType] = mapped_column(Enum(InteractionType))
    context: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
