"""Agent service — autonomous task execution with tool use.

Agents are spawned when items are classified as actionable (e.g., "research X",
"compare Y and Z", "find information about W"). They execute multi-step plans
using available tools and store results as linked items.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.agent_task import AgentTask, AgentTaskType, AgentTaskStatus
from app.models.item import Item, ItemType, ItemStatus, EnrichmentStatus
from app.services.ai_service import chat_completion
from app.services.context_service import assemble_context
from app.services.embedding_service import hybrid_search
from app.services.capture_service import quick_capture

logger = logging.getLogger(__name__)

# Maximum steps to prevent infinite loops
MAX_AGENT_STEPS = 8

# Tools available to the agent
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search the user's items and memories semantically to find relevant information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "Create a new reference note with findings or research results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the note",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full content of the note",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to apply to the note",
                    },
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize",
            "description": "Produce a concise summary of provided text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to summarize",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information. Returns search results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Signal that the task is complete and provide a final summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A clear summary of what was accomplished",
                    },
                },
                "required": ["summary"],
            },
        },
    },
]


def detect_agent_task_type(content: str, ai_metadata: dict | None = None) -> AgentTaskType | None:
    """Detect if an item should spawn an agent task and what type."""
    if ai_metadata and ai_metadata.get("is_actionable_by_agent"):
        # LLM already flagged it
        pass
    else:
        # Heuristic detection
        content_lower = content.lower()
        triggers = {
            "research": ["research", "look up", "look into", "investigate", "find out about"],
            "summarize": ["summarize", "summary of", "recap", "brief me on"],
            "find": ["find", "search for", "locate", "where can i"],
            "compare": ["compare", "vs", "versus", "difference between", "which is better"],
            "plan": ["plan", "outline", "strategy for", "how should i"],
        }
        detected = None
        for task_type, keywords in triggers.items():
            if any(kw in content_lower for kw in keywords):
                detected = task_type
                break
        if not detected:
            return None

    # Map to enum
    content_lower = content.lower()
    if any(w in content_lower for w in ["research", "investigate", "look up", "find out"]):
        return AgentTaskType.research
    elif any(w in content_lower for w in ["summarize", "summary", "recap"]):
        return AgentTaskType.summarize
    elif any(w in content_lower for w in ["compare", "vs", "versus"]):
        return AgentTaskType.compare
    elif any(w in content_lower for w in ["find", "search", "locate"]):
        return AgentTaskType.find
    elif any(w in content_lower for w in ["plan", "outline", "strategy"]):
        return AgentTaskType.plan
    else:
        return AgentTaskType.custom


async def create_agent_task(
    db: AsyncSession,
    source_item_id: uuid.UUID | None,
    prompt: str,
    task_type: AgentTaskType = AgentTaskType.custom,
) -> AgentTask:
    """Create a new agent task and enqueue it for execution."""
    task = AgentTask(
        source_item_id=source_item_id,
        task_type=task_type,
        prompt=prompt,
        status=AgentTaskStatus.pending,
        steps=[],
    )
    db.add(task)
    await db.commit()

    # Enqueue for worker
    await _enqueue_agent_task(str(task.id))
    return task


async def _enqueue_agent_task(task_id: str):
    """Push agent task to Redis queue."""
    import redis.asyncio as aioredis
    from app.core.config import settings

    r = aioredis.from_url(settings.redis_url)
    try:
        await r.rpush(
            "arq:queue",
            json.dumps({"function": "run_agent", "args": [task_id]}),
        )
    finally:
        await r.close()


async def _execute_tool(db: AsyncSession, tool_name: str, args: dict, task: AgentTask) -> str:
    """Execute an agent tool and return the result string."""
    if tool_name == "search_memory":
        query = args.get("query", "")
        try:
            results = await hybrid_search(db, query, limit=5)
            if results:
                lines = []
                for item, score in results:
                    lines.append(f"- [{item.item_type.value if item.item_type else '?'}] {item.content[:200]} (relevance: {score:.2f})")
                return "\n".join(lines)
            return "No relevant items found."
        except Exception as e:
            return f"Search failed: {e}"

    elif tool_name == "create_note":
        title = args.get("title", "Agent Note")
        content = args.get("content", "")
        tags = args.get("tags", [])
        full_content = f"{title}\n\n{content}"
        item = await quick_capture(db, full_content, tags)
        item.item_type = ItemType.reference
        item.parsed_title = title
        item.enrichment_status = EnrichmentStatus.complete
        item.status = ItemStatus.active

        # Link to source item
        if task.source_item_id:
            item.parent_id = task.source_item_id

        # Track created item
        result_items = task.result_items or []
        result_items.append(str(item.id))
        task.result_items = result_items

        await db.flush()
        return f"Created note: '{title}' (id: {item.id})"

    elif tool_name == "summarize":
        text = args.get("text", "")
        if not text:
            return "No text provided to summarize."
        try:
            response = await chat_completion([
                {"role": "system", "content": "You are a concise summarizer. Produce a clear, brief summary."},
                {"role": "user", "content": f"Summarize the following:\n\n{text[:4000]}"},
            ])
            return response.get("message", {}).get("content", "Summary unavailable.")
        except Exception as e:
            return f"Summarization failed: {e}"

    elif tool_name == "web_search":
        query = args.get("query", "")
        # Web search is a best-effort feature — requires SearXNG or similar
        # For now, the LLM will use its training knowledge when web search isn't available
        return (
            f"Web search for '{query}' is not currently available. "
            "Use your existing knowledge to answer, or use search_memory "
            "to check the user's existing items."
        )

    elif tool_name == "finish":
        return args.get("summary", "Task complete.")

    return f"Unknown tool: {tool_name}"


async def run_agent(ctx: dict, task_id: str):
    """Execute an agent task autonomously.

    The agent runs in a loop:
    1. Build context with the task prompt + previous steps
    2. Call LLM with available tools
    3. Execute any tool calls
    4. Repeat until 'finish' is called or max steps reached
    """
    from app.routers.events import publish_event

    async with async_session() as db:
        result = await db.execute(
            select(AgentTask).where(AgentTask.id == uuid.UUID(task_id))
        )
        task = result.scalar_one_or_none()
        if not task:
            logger.error(f"Agent task {task_id} not found")
            return

        task.status = AgentTaskStatus.running
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Notify UI that agent started
        await publish_event("agent_started", {
            "task_id": task_id,
            "prompt": task.prompt[:200],
        })

        try:
            # Build initial context
            context_messages = await assemble_context(
                db, task.prompt, include_corrections=False, include_recent=True
            )

            # Agent system prompt
            agent_system = (
                "You are an autonomous agent executing a task for the user. "
                "You have tools available to search the user's items, create notes, "
                "summarize text, and search the web. "
                "Work step by step to accomplish the task. "
                "When you are done, call the 'finish' tool with a summary. "
                "Be thorough but concise."
            )
            messages = [{"role": "system", "content": agent_system}]
            messages.extend(context_messages[1:])  # Skip default persona, use agent system
            messages.append({"role": "user", "content": f"Task: {task.prompt}"})

            steps = []

            for step_num in range(MAX_AGENT_STEPS):
                response = await chat_completion(messages, tools=AGENT_TOOLS)
                ai_message = response.get("message", {})
                content = ai_message.get("content", "")
                tool_calls = ai_message.get("tool_calls")

                if content:
                    messages.append({"role": "assistant", "content": content})

                if not tool_calls:
                    # No tool calls — agent is done (or stuck)
                    steps.append({
                        "action": "thinking",
                        "result": content[:500],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    break

                # Process tool calls
                for call in tool_calls:
                    func_name = call.get("function", {}).get("name", "")
                    raw_args = call.get("function", {}).get("arguments", {})
                    # Normalize args — some models return JSON string instead of dict
                    if isinstance(raw_args, str):
                        try:
                            func_args = json.loads(raw_args)
                        except (ValueError, TypeError):
                            func_args = {}
                    else:
                        func_args = raw_args if isinstance(raw_args, dict) else {}

                    tool_result = await _execute_tool(db, func_name, func_args, task)

                    steps.append({
                        "action": f"{func_name}({json.dumps(func_args)[:200]})",
                        "result": tool_result[:500],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                    # Publish step progress
                    await publish_event("agent_step", {
                        "task_id": task_id,
                        "step": step_num + 1,
                        "action": func_name,
                    })

                    if func_name == "finish":
                        task.result_summary = func_args.get("summary", tool_result)
                        break

                    # Add tool result to conversation
                    messages.append({
                        "role": "user",
                        "content": f"Tool result ({func_name}): {tool_result}",
                    })

                # Check if finished
                if task.result_summary:
                    break

            # If no explicit finish, generate a summary from the last content
            if not task.result_summary:
                task.result_summary = content[:500] if content else "Task completed without explicit summary."

            task.steps = steps
            task.status = AgentTaskStatus.completed
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()

            # Notify UI
            await publish_event("agent_completed", {
                "task_id": task_id,
                "summary": task.result_summary[:300],
                "steps_count": len(steps),
            })

            logger.info(f"Agent task {task_id} completed in {len(steps)} steps")

        except Exception as e:
            logger.error(f"Agent task {task_id} failed: {e}", exc_info=True)
            task.status = AgentTaskStatus.failed
            task.result_summary = f"Failed: {str(e)[:500]}"
            task.steps = steps if 'steps' in dir() else []
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()

            await publish_event("agent_failed", {
                "task_id": task_id,
                "error": str(e)[:200],
            })
