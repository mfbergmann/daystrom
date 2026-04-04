"""Tests for tag management."""

import pytest

SQLITE_NESTED_XFAIL = pytest.mark.xfail(
    reason="SQLite async doesn't support nested queries in capture_service tag lookup"
)


@pytest.mark.asyncio
async def test_list_tags_empty(client):
    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
@SQLITE_NESTED_XFAIL
async def test_tags_created_via_capture(client):
    await client.post("/api/items/capture", json={
        "content": "Test tag creation",
        "tags": ["test-tag"]
    })

    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    tag_names = [t["name"] for t in resp.json()]
    assert "test-tag" in tag_names


@pytest.mark.asyncio
async def test_add_tag_to_item(client):
    resp = await client.post("/api/items/capture", json={"content": "Tag me"})
    item_id = resp.json()["id"]

    resp = await client.post(f"/api/tags/items/{item_id}/tags", json={"tag_name": "new-tag"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "added"

    # Verify tag appears on item
    resp = await client.get(f"/api/items/{item_id}")
    tag_names = [t["name"] for t in resp.json()["tags"]]
    assert "new-tag" in tag_names


@pytest.mark.asyncio
@SQLITE_NESTED_XFAIL
async def test_add_duplicate_tag(client):
    resp = await client.post("/api/items/capture", json={
        "content": "Dup tag test",
        "tags": ["existing"]
    })
    item_id = resp.json()["id"]

    resp = await client.post(f"/api/tags/items/{item_id}/tags", json={"tag_name": "existing"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "already_tagged"


@pytest.mark.asyncio
@SQLITE_NESTED_XFAIL
async def test_remove_tag_from_item(client):
    resp = await client.post("/api/items/capture", json={
        "content": "Remove my tag",
        "tags": ["removable"]
    })
    item_id = resp.json()["id"]

    resp = await client.delete(f"/api/tags/items/{item_id}/tags/removable")
    assert resp.status_code == 200
    assert resp.json()["status"] == "removed"

    # Verify tag is gone
    resp = await client.get(f"/api/items/{item_id}")
    tag_names = [t["name"] for t in resp.json()["tags"]]
    assert "removable" not in tag_names
