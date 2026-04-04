import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Enum, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentTaskType(str, enum.Enum):
    research = "research"
    summarize = "summarize"
    plan = "plan"
    find = "find"
    compare = "compare"
    custom = "custom"


class AgentTaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("items.id"), nullable=True
    )
    task_type: Mapped[AgentTaskType] = mapped_column(Enum(AgentTaskType), default=AgentTaskType.custom)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AgentTaskStatus] = mapped_column(
        Enum(AgentTaskStatus), default=AgentTaskStatus.pending
    )
    steps: Mapped[dict | None] = mapped_column(JSON)  # array of {action, result, timestamp}
    result_summary: Mapped[str | None] = mapped_column(Text)
    result_items: Mapped[dict | None] = mapped_column(JSON)  # array of item UUIDs created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
