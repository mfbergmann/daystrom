"""Tests for agent task management."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_list_agent_tasks_empty(client):
    resp = await client.get("/api/agent-tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert "tasks" in data
    assert "total" in data
    assert isinstance(data["tasks"], list)


@pytest.mark.asyncio
async def test_create_agent_task(client):
    """Creating an agent task should enqueue it."""
    with patch("app.services.agent_service._enqueue_agent_task", new_callable=AsyncMock):
        resp = await client.post("/api/agent-tasks", json={
            "prompt": "Research the best home automation systems",
            "task_type": "research",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["prompt"] == "Research the best home automation systems"
        assert data["task_type"] == "research"
        assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_agent_task(client):
    with patch("app.services.agent_service._enqueue_agent_task", new_callable=AsyncMock):
        resp = await client.post("/api/agent-tasks", json={
            "prompt": "Find the cheapest flights to Tokyo",
        })
        task_id = resp.json()["id"]

        resp = await client.get(f"/api/agent-tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id


@pytest.mark.asyncio
async def test_get_agent_task_not_found(client):
    resp = await client.get("/api/agent-tasks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_agent_task(client):
    with patch("app.services.agent_service._enqueue_agent_task", new_callable=AsyncMock):
        resp = await client.post("/api/agent-tasks", json={
            "prompt": "Cancel me",
        })
        task_id = resp.json()["id"]

        resp = await client.post(f"/api/agent-tasks/{task_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_completed_task_fails(client):
    """Cannot cancel a task that's already completed."""
    with patch("app.services.agent_service._enqueue_agent_task", new_callable=AsyncMock):
        resp = await client.post("/api/agent-tasks", json={
            "prompt": "Already done",
        })
        task_id = resp.json()["id"]

        # Cancel it first
        await client.post(f"/api/agent-tasks/{task_id}/cancel")

        # Try to cancel again (now it's cancelled, not pending/running)
        resp = await client.post(f"/api/agent-tasks/{task_id}/cancel")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_agent_task_no_prompt(client):
    resp = await client.post("/api/agent-tasks", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_filter_agent_tasks_by_status(client):
    with patch("app.services.agent_service._enqueue_agent_task", new_callable=AsyncMock):
        # Create a task
        await client.post("/api/agent-tasks", json={"prompt": "Filter test"})

        resp = await client.get("/api/agent-tasks?status=pending")
        assert resp.status_code == 200
        for task in resp.json()["tasks"]:
            assert task["status"] == "pending"


@pytest.mark.asyncio
async def test_agent_task_type_detection():
    """Test the heuristic agent task type detection."""
    from app.services.agent_service import detect_agent_task_type
    from app.models.agent_task import AgentTaskType

    assert detect_agent_task_type("Research the best home automation") == AgentTaskType.research
    assert detect_agent_task_type("Summarize the meeting notes") == AgentTaskType.summarize
    assert detect_agent_task_type("Compare React vs Vue") == AgentTaskType.compare
    assert detect_agent_task_type("Find the cheapest option") == AgentTaskType.find
    assert detect_agent_task_type("Plan my weekend trip") == AgentTaskType.plan
    assert detect_agent_task_type("Buy milk") is None  # Not an agent task
