"""LLM service wrapping Ollama via its OpenAI-compatible API."""

import json
import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OLLAMA_CHAT_URL = f"{settings.ollama_base_url}/api/chat"
OLLAMA_EMBED_URL = f"{settings.ollama_base_url}/api/embed"
OLLAMA_TAGS_URL = f"{settings.ollama_base_url}/api/tags"

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=120.0)
    return _client


async def check_ollama() -> bool:
    try:
        resp = await _get_client().get(OLLAMA_TAGS_URL, timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,
) -> dict:
    """Single-turn chat completion. Returns the full response dict."""
    payload = {
        "model": model or settings.ollama_model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    resp = await _get_client().post(OLLAMA_CHAT_URL, json=payload)
    resp.raise_for_status()
    return resp.json()


async def chat_stream(
    messages: list[dict],
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Streaming chat completion. Yields content tokens."""
    payload = {
        "model": model or settings.ollama_model,
        "messages": messages,
        "stream": True,
    }

    async with _get_client().stream("POST", OLLAMA_CHAT_URL, json=payload) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
            except json.JSONDecodeError:
                continue


async def generate_embedding(text: str, model: str | None = None) -> list[float]:
    """Generate an embedding vector for text."""
    payload = {
        "model": model or settings.ollama_embed_model,
        "input": text,
    }
    resp = await _get_client().post(OLLAMA_EMBED_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings", [])
    if embeddings:
        return embeddings[0]
    raise ValueError("No embedding returned from Ollama")
