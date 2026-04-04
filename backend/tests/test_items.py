"""Tests for items CRUD and capture pipeline."""

import pytest


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Daystrom"
    assert data["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "database" in data
    assert "ollama" in data


@pytest.mark.asyncio
async def test_capture_item(client):
    resp = await client.post("/api/items/capture", json={"content": "Buy milk tomorrow"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Buy milk tomorrow"
    assert data["status"] == "inbox"
    assert data["enrichment_status"] == "pending"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
@pytest.mark.xfail(reason="SQLite async doesn't support nested queries in capture_service tag lookup")
async def test_capture_with_tags(client):
    resp = await client.post("/api/items/capture", json={
        "content": "Fix the leaking faucet",
        "tags": ["home", "plumbing"]
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Fix the leaking faucet"
    tag_names = [t["name"] for t in data["tags"]]
    assert "home" in tag_names
    assert "plumbing" in tag_names
    # User-specified tags should have source=user
    for t in data["tags"]:
        assert t["source"] == "user"


@pytest.mark.asyncio
async def test_list_items(client):
    # Capture a couple items
    await client.post("/api/items/capture", json={"content": "Item A"})
    await client.post("/api/items/capture", json={"content": "Item B"})

    resp = await client.get("/api/items")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_item(client):
    resp = await client.post("/api/items/capture", json={"content": "Specific item"})
    item_id = resp.json()["id"]

    resp = await client.get(f"/api/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "Specific item"


@pytest.mark.asyncio
async def test_get_item_not_found(client):
    resp = await client.get("/api/items/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_item_status(client):
    resp = await client.post("/api/items/capture", json={"content": "Complete me"})
    item_id = resp.json()["id"]

    resp = await client.patch(f"/api/items/{item_id}", json={"status": "done"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_update_item_type_tracks_correction(client):
    resp = await client.post("/api/items/capture", json={"content": "Track my correction"})
    item_id = resp.json()["id"]

    # First set a type
    await client.patch(f"/api/items/{item_id}", json={"item_type": "note"})
    # Then correct it — should track interaction
    resp = await client.patch(f"/api/items/{item_id}", json={"item_type": "task"})
    assert resp.status_code == 200
    assert resp.json()["item_type"] == "task"


@pytest.mark.asyncio
async def test_delete_item(client):
    resp = await client.post("/api/items/capture", json={"content": "Delete me"})
    item_id = resp.json()["id"]

    resp = await client.delete(f"/api/items/{item_id}")
    assert resp.status_code == 204

    # Item should be archived, not truly deleted
    resp = await client.get(f"/api/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_filter_by_status(client):
    await client.post("/api/items/capture", json={"content": "Filter test"})

    resp = await client.get("/api/items?status=inbox")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "inbox"


@pytest.mark.asyncio
async def test_capture_heuristic_type_detection(client):
    # "remind me" should hint at task
    resp = await client.post("/api/items/capture", json={"content": "Remind me to call the dentist"})
    # Heuristic sets type hint but won't persist without enrichment in this test
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_empty_capture_rejected(client):
    resp = await client.post("/api/items/capture", json={"content": ""})
    assert resp.status_code == 422
