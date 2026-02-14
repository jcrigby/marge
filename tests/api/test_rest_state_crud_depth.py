"""
CTS -- REST State CRUD Depth Tests

Tests the core REST API state operations: POST /api/states/{entity_id}
(create/update), GET /api/states (list all), GET /api/states/{entity_id}
(single), and comprehensive response format verification.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── POST /api/states (create) ──────────────────────────

async def test_create_entity_via_post(rest):
    """POST /api/states/{entity_id} creates a new entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_c_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "42"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == eid
    assert data["state"] == "42"


async def test_create_entity_with_attributes(rest):
    """POST creates entity with attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_ca_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "99", "attributes": {"unit": "W", "friendly_name": "Power"}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["attributes"]["unit"] == "W"
    assert data["attributes"]["friendly_name"] == "Power"


async def test_create_entity_response_has_timestamps(rest):
    """POST response includes timestamps."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_ts_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "1"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert "last_changed" in data
    assert "last_updated" in data


async def test_create_entity_response_has_context(rest):
    """POST response includes context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_ctx_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "1"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert "context" in data
    assert "id" in data["context"]


# ── POST /api/states (update) ──────────────────────────

async def test_update_entity_state(rest):
    """POST to existing entity updates state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_u_{tag}"
    await rest.set_state(eid, "A")
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "B"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "B"


async def test_update_entity_attributes(rest):
    """POST to existing entity updates attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_ua_{tag}"
    await rest.set_state(eid, "1", {"unit": "W"})
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "2", "attributes": {"unit": "kW"}},
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["state"] == "2"
    assert data["attributes"]["unit"] == "kW"


# ── GET /api/states (list) ─────────────────────────────

async def test_get_states_returns_list(rest):
    """GET /api/states returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_get_states_includes_entity(rest):
    """GET /api/states includes a created entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_li_{tag}"
    await rest.set_state(eid, "1")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    data = resp.json()
    eids = [e["entity_id"] for e in data]
    assert eid in eids


async def test_get_states_entries_have_fields(rest):
    """GET /api/states entries have standard fields."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_fl_{tag}"
    await rest.set_state(eid, "42")
    states = await rest.get_states()
    entry = next(s for s in states if s["entity_id"] == eid)
    assert "state" in entry
    assert "attributes" in entry
    assert "last_changed" in entry
    assert "last_updated" in entry
    assert "context" in entry


# ── GET /api/states/{entity_id} ────────────────────────

async def test_get_single_entity(rest):
    """GET /api/states/{entity_id} returns single entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.crud_gs_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == eid
    assert data["state"] == "42"


async def test_get_nonexistent_entity_404(rest):
    """GET /api/states for non-existent entity returns 404."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.nonexistent_crud_99",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Domain Variety ──────────────────────────────────────

async def test_create_various_domains(rest):
    """Can create entities across different domains."""
    tag = uuid.uuid4().hex[:8]
    domains = ["sensor", "light", "switch", "binary_sensor", "lock", "climate", "cover"]
    for domain in domains:
        eid = f"{domain}.crud_dom_{tag}"
        await rest.set_state(eid, "test")
        state = await rest.get_state(eid)
        assert state["entity_id"] == eid
