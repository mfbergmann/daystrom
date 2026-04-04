"""Chat service — manages conversations and streams AI responses."""

import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation, ChatMessage
from app.models.interaction import Interaction, InteractionType
from app.services.ai_service import chat_stream, chat_completion
from app.services.context_service import assemble_context
from app.services.capture_service import quick_capture

logger = logging.getLogger(__name__)

# Tools the chat AI can invoke
CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_item",
            "description": "Create a new todo item, idea, or note for the user. Use when the user asks to add, create, or remember something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The natural language content of the item",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags to apply",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_items",
            "description": "Search the user's items semantically. Use when the user asks about existing items or wants to find something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


async def get_or_create_conversation(
    db: AsyncSession, conversation_id: uuid.UUID | None = None
) -> Conversation:
    """Get existing conversation or create a new one."""
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    conv = Conversation()
    db.add(conv)
    await db.flush()
    return conv


async def list_conversations(db: AsyncSession, limit: int = 20, offset: int = 0) -> list[dict]:
    """List conversations ordered by most recent, with message counts."""
    from sqlalchemy import func as sa_func

    stmt = (
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    convs = list(result.scalars().all())

    # Get message counts efficiently
    conv_data = []
    for c in convs:
        count_stmt = select(sa_func.count()).where(ChatMessage.conversation_id == c.id)
        count = (await db.execute(count_stmt)).scalar() or 0
        conv_data.append({
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": count,
        })
    return conv_data


async def get_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation | None:
    """Get a single conversation (without lazy-loading messages)."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_conversation_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[ChatMessage]:
    """Load conversation messages eagerly to avoid lazy-loading issues."""
    from sqlalchemy import select as sa_select
    stmt = (
        sa_select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _count_conversation_messages(db: AsyncSession, conversation_id: uuid.UUID) -> int:
    """Count messages in a conversation."""
    from sqlalchemy import func as sa_func
    stmt = select(sa_func.count()).where(ChatMessage.conversation_id == conversation_id)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _build_chat_messages(
    db: AsyncSession, conversation: Conversation, user_message: str
) -> list[dict]:
    """Build the full message list for the LLM: context + history + new message."""
    # Get context (persona, memories, recent items, corrections)
    context_messages = await assemble_context(
        db, user_message, include_corrections=True, include_recent=True
    )

    # Add conversation history (eagerly loaded to avoid SQLite issues)
    messages = list(context_messages)
    history = await _get_conversation_messages(db, conversation.id)
    for msg in history:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    # Add the new user message
    messages.append({"role": "user", "content": user_message})
    return messages


async def _handle_tool_calls(db: AsyncSession, tool_calls: list[dict]) -> list[dict]:
    """Execute tool calls from the AI and return results."""
    results = []
    for call in tool_calls:
        func_name = call.get("function", {}).get("name", "")
        args = call.get("function", {}).get("arguments", {})

        if func_name == "create_item":
            content = args.get("content", "")
            tags = args.get("tags")
            if content:
                item = await quick_capture(db, content, tags)
                # Enqueue enrichment
                try:
                    from app.workers.enrichment import enqueue_enrichment
                    await enqueue_enrichment(str(item.id))
                except Exception:
                    pass
                results.append({
                    "tool": func_name,
                    "result": f"Created item: '{content}' (id: {item.id})",
                })
            else:
                results.append({"tool": func_name, "result": "Error: no content provided"})

        elif func_name == "search_items":
            query = args.get("query", "")
            if query:
                from app.services.embedding_service import hybrid_search
                try:
                    items = await hybrid_search(db, query, limit=5)
                    if items:
                        lines = [f"Found {len(items)} results:"]
                        for item, score in items:
                            status = item.status.value if item.status else "?"
                            lines.append(f"- [{status}] {item.content[:100]} (score: {score:.2f})")
                        results.append({"tool": func_name, "result": "\n".join(lines)})
                    else:
                        results.append({"tool": func_name, "result": "No matching items found."})
                except Exception as e:
                    results.append({"tool": func_name, "result": f"Search error: {e}"})
            else:
                results.append({"tool": func_name, "result": "Error: no query provided"})

        else:
            results.append({"tool": func_name, "result": f"Unknown tool: {func_name}"})

    return results


async def send_message(
    db: AsyncSession,
    conversation: Conversation,
    user_message: str,
) -> str:
    """Send a message and get a non-streaming response (with tool use support)."""
    # Save user message
    user_msg = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.flush()

    # Build messages for LLM
    messages = await _build_chat_messages(db, conversation, user_message)

    # Call LLM with tools
    response = await chat_completion(messages, tools=CHAT_TOOLS)
    ai_message = response.get("message", {})
    content = ai_message.get("content", "")
    tool_calls = ai_message.get("tool_calls")

    # Handle tool calls if present
    if tool_calls:
        tool_results = await _handle_tool_calls(db, tool_calls)

        # Add tool results to messages and get final response
        if content:
            messages.append({"role": "assistant", "content": content})
        tool_summary = "\n".join(
            f"[{r['tool']}]: {r['result']}" for r in tool_results
        )
        messages.append({
            "role": "user",
            "content": f"Tool results:\n{tool_summary}\n\nPlease summarize what was done for the user.",
        })
        final_response = await chat_completion(messages)
        content = final_response.get("message", {}).get("content", content or "Done.")

    # Save assistant message
    assistant_msg = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        tool_calls=tool_calls,
    )
    db.add(assistant_msg)

    # Update conversation title if this is the first exchange
    msg_count = await _count_conversation_messages(db, conversation.id)
    if not conversation.title and msg_count <= 2:
        conversation.title = user_message[:100]

    conversation.updated_at = datetime.now(timezone.utc)

    # Track chat interaction
    interaction = Interaction(
        interaction_type=InteractionType.chat,
        context={"conversation_id": str(conversation.id)},
    )
    db.add(interaction)

    await db.commit()
    return content


async def stream_message(
    db: AsyncSession,
    conversation: Conversation,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """Send a message and stream the response token by token.

    Note: streaming mode doesn't support tool calls — those use send_message.
    For the streaming path, we do a non-streaming tool call first if needed,
    then stream the final response.
    """
    # Save user message
    user_msg = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.flush()

    messages = await _build_chat_messages(db, conversation, user_message)

    # First try with tools (non-streaming) to see if tools are needed
    response = await chat_completion(messages, tools=CHAT_TOOLS)
    ai_message = response.get("message", {})
    tool_calls = ai_message.get("tool_calls")

    if tool_calls:
        # Handle tools, then stream the summary
        tool_results = await _handle_tool_calls(db, tool_calls)
        initial_content = ai_message.get("content", "")
        if initial_content:
            messages.append({"role": "assistant", "content": initial_content})
        tool_summary = "\n".join(
            f"[{r['tool']}]: {r['result']}" for r in tool_results
        )
        messages.append({
            "role": "user",
            "content": f"Tool results:\n{tool_summary}\n\nPlease summarize what was done for the user.",
        })

    # Stream the response
    full_content = ""
    async for token in chat_stream(messages):
        full_content += token
        yield token

    # Save assistant message
    assistant_msg = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=full_content,
        tool_calls=tool_calls,
    )
    db.add(assistant_msg)

    msg_count = await _count_conversation_messages(db, conversation.id)
    if not conversation.title and msg_count <= 2:
        conversation.title = user_message[:100]

    conversation.updated_at = datetime.now(timezone.utc)

    interaction = Interaction(
        interaction_type=InteractionType.chat,
        context={"conversation_id": str(conversation.id)},
    )
    db.add(interaction)

    await db.commit()
