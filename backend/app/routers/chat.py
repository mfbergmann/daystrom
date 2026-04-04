"""Chat router — conversations and streaming AI responses."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.chat import ChatSend, ChatMessageResponse, ConversationResponse
from app.services.chat_service import (
    get_or_create_conversation,
    list_conversations,
    get_conversation,
    send_message,
    stream_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", status_code=200)
async def chat(
    body: ChatSend,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Send a chat message and get a streaming SSE response.

    If Accept header contains text/event-stream, streams tokens via SSE.
    Otherwise returns the complete response as JSON.
    """
    conversation = await get_or_create_conversation(db, body.conversation_id)

    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        # Streaming SSE response
        async def event_generator():
            yield {
                "event": "conversation",
                "data": json.dumps({"conversation_id": str(conversation.id)}),
            }
            async for token in stream_message(db, conversation, body.message):
                yield {
                    "event": "token",
                    "data": json.dumps({"content": token}),
                }
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"}),
            }

        return EventSourceResponse(event_generator())

    # Non-streaming: return complete response
    content = await send_message(db, conversation, body.message)
    return {
        "conversation_id": str(conversation.id),
        "message": content,
    }


@router.get("/conversations")
async def get_conversations(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """List conversations ordered by most recent."""
    return await list_conversations(db, limit=limit, offset=offset)


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Get a conversation with all messages."""
    conv = await get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Eagerly load messages via explicit query
    from app.services.chat_service import _get_conversation_messages
    msgs = await _get_conversation_messages(db, conversation_id)

    return {
        "id": str(conv.id),
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: bool = Depends(get_current_user),
):
    """Delete a conversation and its messages."""
    conv = await get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete messages first, then conversation (eagerly loaded)
    from app.services.chat_service import _get_conversation_messages
    msgs = await _get_conversation_messages(db, conversation_id)
    for msg in msgs:
        await db.delete(msg)
    await db.delete(conv)
    await db.commit()
