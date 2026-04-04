"""Classify and extract structured data from natural language input."""

import json
import logging
import re
from datetime import datetime, timedelta, timezone

from app.services.ai_service import chat_completion

logger = logging.getLogger(__name__)

CLASSIFICATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classify_item",
            "description": "Classify and extract metadata from a user's natural language input",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["task", "idea", "note", "event", "reference"],
                        "description": "The type of item",
                    },
                    "parsed_title": {
                        "type": "string",
                        "description": "A short title (under 80 chars) summarizing the item",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["none", "low", "medium", "high", "urgent"],
                        "description": "Priority level, default to 'none' unless clear urgency",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "ISO 8601 date if a deadline is mentioned, null otherwise",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1-5 relevant tags (lowercase, hyphenated). Categories, topics, people, or projects.",
                    },
                    "is_actionable_by_agent": {
                        "type": "boolean",
                        "description": "True if this is a research/analysis task an AI agent could help with",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "0.0-1.0 confidence in this classification",
                    },
                },
                "required": ["item_type", "parsed_title", "priority", "tags", "confidence"],
            },
        },
    }
]

SYSTEM_PROMPT = """You are Daystrom, an intelligent personal assistant that classifies items.
Given a user's natural language input, classify it and extract structured metadata.

Guidelines:
- task: something the user needs to do (buy, call, fix, send, schedule, etc.)
- idea: a thought, concept, or creative spark to capture
- note: general information, observation, or reference
- event: something happening at a specific time
- reference: a link, resource, or piece of info to save

For tags, use lowercase hyphenated words. Prefer existing common categories.
Set is_actionable_by_agent=true for research tasks, information gathering, comparisons.
Be calibrated with confidence — use lower values when genuinely uncertain."""


def heuristic_preparse(content: str) -> dict:
    """Fast regex-based extraction for common patterns. Runs synchronously."""
    result = {}
    lower = content.lower().strip()

    # Date detection
    today = datetime.now(timezone.utc)
    if "tomorrow" in lower:
        result["due_date_hint"] = (today + timedelta(days=1)).isoformat()
    elif "today" in lower:
        result["due_date_hint"] = today.isoformat()
    elif "next week" in lower:
        result["due_date_hint"] = (today + timedelta(weeks=1)).isoformat()

    # Type hints
    if lower.startswith(("remind me", "don't forget", "need to", "buy ", "call ", "email ")):
        result["type_hint"] = "task"
    elif lower.endswith("?"):
        result["type_hint"] = "idea"
    elif lower.startswith(("idea:", "what if", "maybe ")):
        result["type_hint"] = "idea"
    elif lower.startswith(("note:", "fyi", "btw")):
        result["type_hint"] = "note"

    # Priority hints
    if any(word in lower for word in ("urgent", "asap", "critical", "immediately")):
        result["priority_hint"] = "urgent"
    elif any(word in lower for word in ("important", "high priority")):
        result["priority_hint"] = "high"

    return result


async def classify_item(content: str, context: str = "") -> dict:
    """Use LLM to classify and extract metadata from content.

    Returns dict with: item_type, parsed_title, priority, due_date, tags, confidence, is_actionable_by_agent
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if context:
        messages.append({"role": "system", "content": f"Additional context:\n{context}"})
    messages.append({"role": "user", "content": content})

    try:
        response = await chat_completion(messages, tools=CLASSIFICATION_TOOLS)
        message = response.get("message", {})

        # Check for tool calls
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            args = tool_calls[0].get("function", {}).get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            return args

        # Fallback: try to parse content as JSON
        content_text = message.get("content", "")
        try:
            return json.loads(content_text)
        except (json.JSONDecodeError, TypeError):
            pass

    except Exception as e:
        logger.error(f"Classification failed: {e}")

    # Fallback classification
    hints = heuristic_preparse(content)
    return {
        "item_type": hints.get("type_hint", "note"),
        "parsed_title": content[:80],
        "priority": hints.get("priority_hint", "none"),
        "tags": [],
        "confidence": 0.3,
        "is_actionable_by_agent": False,
    }
