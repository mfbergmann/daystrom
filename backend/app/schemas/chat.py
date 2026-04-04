from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSend(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: UUID | None = None


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = []

    model_config = {"from_attributes": True}
