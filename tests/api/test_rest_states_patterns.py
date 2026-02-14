"""
CTS -- REST States Endpoint Pattern Tests

Tests GET /api/states, POST /api/states/{entity_id}, DELETE /api/states/{entity_id}
patterns including large payloads, special characters, attribute types, and
concurrent operations.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_get_states_returns_list(rest):
    """GET /api/states returns list of all entities."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_set_state_creates_entity(rest):
    """POST /api/states/{eid} creates a new entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.new_{tag}"

    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "hello", "attributes": {"friendly_name": "New Entity"}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "hello"
    assert state["attributes"]["friendly_name"] == "New Entity"


async def test_set_state_updates_existing(rest):
    """POST to existing entity updates its state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.upd_{tag}"
    await rest.set_state(eid, "old")

    await rest.set_state(eid, "new")
    state = await rest.get_state(eid)
    assert state["state"] == "new"


async def test_delete_state_removes_entity(rest):
    """DELETE /api/states/{eid} removes entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_{tag}"
    await rest.set_state(eid, "temp")

    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp2.status_code == 404


async def test_delete_nonexistent_returns_404(rest):
    """DELETE on nonexistent entity returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.definitely_gone_999",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_get_nonexistent_returns_404(rest):
    """GET on nonexistent entity returns 404."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.missing_xyz_999",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_set_state_with_numeric_string(rest):
    """State value as numeric string preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.num_{tag}"
    await rest.set_state(eid, "42.5")

    state = await rest.get_state(eid)
    assert state["state"] == "42.5"


async def test_set_state_with_boolean_attributes(rest):
    """Boolean attribute values preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.bool_{tag}"
    await rest.set_state(eid, "on", {"is_active": True, "is_disabled": False})

    state = await rest.get_state(eid)
    assert state["attributes"]["is_active"] is True
    assert state["attributes"]["is_disabled"] is False


async def test_set_state_with_nested_attributes(rest):
    """Nested object attributes preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.nested_{tag}"
    await rest.set_state(eid, "complex", {
        "config": {"interval": 30, "enabled": True},
        "tags": ["indoor", "primary"],
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["config"]["interval"] == 30
    assert "indoor" in state["attributes"]["tags"]


async def test_set_state_empty_string(rest):
    """Empty string state is valid."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.empty_{tag}"
    await rest.set_state(eid, "")

    state = await rest.get_state(eid)
    assert state["state"] == ""


async def test_set_state_long_value(rest):
    """Long state value (1000 chars) works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.long_{tag}"
    long_val = "x" * 1000
    await rest.set_state(eid, long_val)

    state = await rest.get_state(eid)
    assert len(state["state"]) == 1000


async def test_entity_id_with_underscores(rest):
    """Entity ID with multiple underscores works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.multi_word_name_{tag}"
    await rest.set_state(eid, "val")

    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


async def test_set_state_response_has_entity_fields(rest):
    """POST response includes entity_id, state, attributes, context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.resp_{tag}"

    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "val", "attributes": {}},
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["entity_id"] == eid
    assert data["state"] == "val"
    assert "context" in data
    assert "last_changed" in data
