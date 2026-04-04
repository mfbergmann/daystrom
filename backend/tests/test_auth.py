"""Tests for authentication."""

import pytest
from app.core.config import settings


@pytest.mark.asyncio
async def test_auth_status_no_pin(client):
    resp = await client.get("/api/auth/status")
    assert resp.status_code == 200
    assert resp.json()["auth_required"] is False


@pytest.mark.asyncio
async def test_login_no_pin_required(client):
    resp = await client.post("/api/auth/login", json={"pin": "anything"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_classifier_heuristics():
    """Test heuristic_preparse without LLM."""
    from app.services.classifier import heuristic_preparse

    result = heuristic_preparse("Buy milk tomorrow")
    assert result.get("type_hint") == "task"
    assert "due_date_hint" in result

    result = heuristic_preparse("What if we tried a different approach?")
    assert result.get("type_hint") == "idea"

    result = heuristic_preparse("Note: meeting moved to 3pm")
    assert result.get("type_hint") == "note"

    result = heuristic_preparse("URGENT fix the production server")
    assert result.get("priority_hint") == "urgent"

    result = heuristic_preparse("This is important to finish")
    assert result.get("priority_hint") == "high"

    result = heuristic_preparse("Just a random thought")
    assert result == {}
