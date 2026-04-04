"""Server-Sent Events endpoint for real-time updates."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


async def _event_generator(request: Request):
    """Subscribe to Redis pub/sub and yield SSE events."""
    r = aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe("daystrom:events")

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    event_data = json.loads(data)
                    yield {
                        "event": event_data.get("event", "update"),
                        "data": json.dumps(event_data.get("data", {})),
                    }
                except json.JSONDecodeError:
                    yield {"event": "message", "data": data}
            else:
                # Send keepalive
                yield {"event": "ping", "data": ""}
                await asyncio.sleep(1)
    finally:
        await pubsub.unsubscribe("daystrom:events")
        await pubsub.close()
        await r.close()


@router.get("")
async def event_stream(
    request: Request,
    _user: bool = Depends(get_current_user),
):
    """SSE stream for real-time updates: enrichment, agent progress, etc."""
    return EventSourceResponse(_event_generator(request))


async def publish_event(event_type: str, data: dict):
    """Publish an event to all connected SSE clients."""
    r = aioredis.from_url(settings.redis_url)
    try:
        payload = json.dumps({"event": event_type, "data": data})
        await r.publish("daystrom:events", payload)
    finally:
        await r.close()
