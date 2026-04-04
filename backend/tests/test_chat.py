"""Tests for chat conversations and messaging."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_list_conversations_empty(client):
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_chat_creates_conversation(client):
    """Non-streaming chat should create a conversation and return a response."""
    mock_response = {
        "message": {
            "content": "Hello! How can I help you today?",
            "role": "assistant",
        }
    }
    with patch("app.services.chat_service.chat_completion", new_callable=AsyncMock, return_value=mock_response):
        with patch("app.services.chat_service.assemble_context", new_callable=AsyncMock, return_value=[
            {"role": "system", "content": "You are Daystrom."}
        ]):
            resp = await client.post("/api/chat", json={
                "message": "Hello Daystrom"
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "conversation_id" in data
            assert "message" in data
            assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_chat_continues_conversation(client):
    """Sending a second message to the same conversation should work."""
    mock_response = {
        "message": {
            "content": "I'm here to help!",
            "role": "assistant",
        }
    }
    with patch("app.services.chat_service.chat_completion", new_callable=AsyncMock, return_value=mock_response):
        with patch("app.services.chat_service.assemble_context", new_callable=AsyncMock, return_value=[
            {"role": "system", "content": "You are Daystrom."}
        ]):
            # First message
            resp1 = await client.post("/api/chat", json={"message": "First message"})
            assert resp1.status_code == 200
            conv_id = resp1.json()["conversation_id"]

            # Second message to same conversation
            resp2 = await client.post("/api/chat", json={
                "message": "Second message",
                "conversation_id": conv_id,
            })
            assert resp2.status_code == 200
            assert resp2.json()["conversation_id"] == conv_id


@pytest.mark.asyncio
async def test_get_conversation(client):
    """Get a specific conversation with messages."""
    mock_response = {
        "message": {"content": "Test response", "role": "assistant"}
    }
    with patch("app.services.chat_service.chat_completion", new_callable=AsyncMock, return_value=mock_response):
        with patch("app.services.chat_service.assemble_context", new_callable=AsyncMock, return_value=[
            {"role": "system", "content": "You are Daystrom."}
        ]):
            resp = await client.post("/api/chat", json={"message": "Get me"})
            conv_id = resp.json()["conversation_id"]

            resp = await client.get(f"/api/conversations/{conv_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == conv_id
            assert len(data["messages"]) == 2  # user + assistant


@pytest.mark.asyncio
async def test_get_conversation_not_found(client):
    resp = await client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation(client):
    mock_response = {
        "message": {"content": "Delete me", "role": "assistant"}
    }
    with patch("app.services.chat_service.chat_completion", new_callable=AsyncMock, return_value=mock_response):
        with patch("app.services.chat_service.assemble_context", new_callable=AsyncMock, return_value=[
            {"role": "system", "content": "You are Daystrom."}
        ]):
            resp = await client.post("/api/chat", json={"message": "Delete test"})
            conv_id = resp.json()["conversation_id"]

            resp = await client.delete(f"/api/conversations/{conv_id}")
            assert resp.status_code == 204

            # Should be gone
            resp = await client.get(f"/api/conversations/{conv_id}")
            assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_with_tool_calls(client):
    """Chat that triggers tool calls (e.g., create_item)."""
    # First call returns tool call, second returns summary
    tool_response = {
        "message": {
            "content": "",
            "role": "assistant",
            "tool_calls": [{
                "function": {
                    "name": "create_item",
                    "arguments": {"content": "Buy groceries", "tags": ["shopping"]},
                }
            }],
        }
    }
    summary_response = {
        "message": {"content": "I've created a task to buy groceries for you!", "role": "assistant"}
    }
    call_count = {"n": 0}

    async def mock_chat_completion(messages, tools=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return tool_response
        return summary_response

    with patch("app.services.chat_service.chat_completion", side_effect=mock_chat_completion):
        with patch("app.services.chat_service.assemble_context", new_callable=AsyncMock, return_value=[
            {"role": "system", "content": "You are Daystrom."}
        ]):
            with patch("app.workers.enrichment.enqueue_enrichment", new_callable=AsyncMock):
                resp = await client.post("/api/chat", json={
                    "message": "Add buy groceries to my list"
                })
                assert resp.status_code == 200
                assert "groceries" in resp.json()["message"].lower()
