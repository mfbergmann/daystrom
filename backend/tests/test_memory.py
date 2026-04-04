"""Tests for memory and learning endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_memories_empty(client):
    resp = await client.get("/api/memories")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_memory_stats(client):
    resp = await client.get("/api/memories/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_type" in data
    assert "avg_confidence" in data


@pytest.mark.asyncio
async def test_behavioral_model(client):
    resp = await client.get("/api/learning/model")
    assert resp.status_code == 200
    data = resp.json()
    assert "type_distribution" in data
    assert "task_completion_rate" in data
    assert "tag_affinity" in data
    assert "capture_hours" in data


@pytest.mark.asyncio
async def test_interactions_list(client):
    resp = await client.get("/api/learning/interactions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
