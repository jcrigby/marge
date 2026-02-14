"""
CTS -- Entity Delete and Purge Tests

Tests DELETE /api/states/<entity_id> for single entity removal,
and search with label/area filter parameters.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Single Entity Delete ─────────────────────────────────

async def test_delete_entity(rest):
    """DELETE /api/states/<entity_id> removes the entity."""
    entity_id = "sensor.delete_test"
    await rest.set_state(entity_id, "42")

    # Verify it exists
    state = await rest.get_state(entity_id)
    assert state is not None

    # Delete it
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify gone
    state = await rest.get_state(entity_id)
    assert state is None


async def test_delete_nonexistent_returns_404(rest):
    """DELETE for nonexistent entity returns 404."""
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.does_not_exist_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_delete_then_recreate(rest):
    """Deleted entity can be recreated."""
    entity_id = "sensor.delete_recreate_test"
    await rest.set_state(entity_id, "first")

    # Delete
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/{entity_id}",
        headers=rest._headers(),
    )

    # Recreate
    result = await rest.set_state(entity_id, "second")
    assert result["state"] == "second"

    # Verify it's back
    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["state"] == "second"


async def test_delete_reduces_entity_count(rest):
    """Deleting an entity reduces the count in /api/states."""
    entity_id = "sensor.delete_count_test"
    await rest.set_state(entity_id, "temp")

    states_before = await rest.get_states()
    count_before = len(states_before)

    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/{entity_id}",
        headers=rest._headers(),
    )

    states_after = await rest.get_states()
    assert len(states_after) == count_before - 1


# ── Search with Label Filter ────────────────────────────

async def test_search_by_label(rest):
    """Search with label= filter returns only labeled entities."""
    # Create label and entity
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": "search_label_test", "name": "Test Label"},
        headers=rest._headers(),
    )
    await rest.set_state("sensor.labeled_search", "99")
    await rest.set_state("sensor.unlabeled_search", "88")

    # Assign label
    await rest.client.post(
        f"{rest.base_url}/api/labels/search_label_test/entities/sensor.labeled_search",
        headers=rest._headers(),
    )

    # Search
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label=search_label_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    ids = [r["entity_id"] for r in results]
    assert "sensor.labeled_search" in ids
    assert "sensor.unlabeled_search" not in ids

    # Cleanup
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/search_label_test/entities/sensor.labeled_search",
        headers=rest._headers(),
    )
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/search_label_test",
        headers=rest._headers(),
    )


async def test_search_by_area(rest):
    """Search with area= filter returns only entities in that area."""
    # Create area and entity
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": "search_area_test", "name": "Search Room"},
        headers=rest._headers(),
    )
    await rest.set_state("sensor.area_search", "50")
    await rest.set_state("sensor.noarea_search", "60")

    # Assign to area
    await rest.client.post(
        f"{rest.base_url}/api/areas/search_area_test/entities/sensor.area_search",
        headers=rest._headers(),
    )

    # Search
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area=search_area_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    ids = [r["entity_id"] for r in results]
    assert "sensor.area_search" in ids
    assert "sensor.noarea_search" not in ids

    # Cleanup
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/search_area_test/entities/sensor.area_search",
        headers=rest._headers(),
    )
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/search_area_test",
        headers=rest._headers(),
    )
