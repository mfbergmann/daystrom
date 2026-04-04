"""Tests for learning service, digest, and tag merge suggestions."""

import pytest
from app.services.learning_service import suggest_tag_merges, refine_classification_prompt


@pytest.mark.asyncio
async def test_daily_digest(client):
    """Digest endpoint should return activity summary."""
    resp = await client.get("/api/learning/digest")
    assert resp.status_code == 200
    data = resp.json()
    assert "items_captured" in data
    assert "items_completed" in data
    assert "items_overdue" in data
    assert "new_memories" in data
    assert "tag_merge_suggestions" in data
    assert "period" in data


@pytest.mark.asyncio
async def test_tag_merge_suggestions(client):
    """Tag merge suggestions endpoint should return a list."""
    resp = await client.get("/api/learning/tag-merge-suggestions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_tag_merge_detection(db):
    """Tags with similar names should be detected as merge candidates."""
    from app.models.tag import Tag

    # Create tags that should be merge candidates
    db.add(Tag(name="home-improvement", usage_count=3))
    db.add(Tag(name="homeimprovement", usage_count=1))
    db.add(Tag(name="work_tasks", usage_count=5))
    db.add(Tag(name="work-tasks", usage_count=2))
    await db.commit()

    suggestions = await suggest_tag_merges(db)
    names = [(s["source"], s["target"]) for s in suggestions]

    # homeimprovement should merge into home-improvement (hyphenation variant)
    assert any("homeimprovement" in pair for pair in names)
    # work_tasks / work-tasks should be detected (separator variant)
    assert any("work_tasks" in pair or "work-tasks" in pair for pair in names)


@pytest.mark.asyncio
async def test_classification_refinement_needs_corrections(db):
    """Refinement should return None when there aren't enough corrections."""
    result = await refine_classification_prompt(db)
    assert result is None  # No corrections yet


@pytest.mark.asyncio
async def test_behavioral_model_endpoint(client):
    resp = await client.get("/api/learning/model")
    assert resp.status_code == 200
    data = resp.json()
    assert "capture_hours" in data
    assert "type_distribution" in data
    assert "task_completion_rate" in data
