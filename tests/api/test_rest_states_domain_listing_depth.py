"""
CTS -- REST States Domain Listing Depth Tests

Tests GET /api/states entity listing: all entities returned,
entity structure fields, domain-specific entities retrievable
by entity_id, and entity count accuracy.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── States Listing ──────────────────────────────────────

async def test_states_returns_200(rest):
    """GET /api/states returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_states_returns_array(rest):
    """GET /api/states returns JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_states_entity_has_required_fields(rest):
    """Each entity in /api/states has entity_id, state, attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rsdl_fld_{tag}"
    await rest.set_state(eid, "test")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    entities = resp.json()
    entity = next((e for e in entities if e["entity_id"] == eid), None)
    assert entity is not None
    assert "state" in entity
    assert "attributes" in entity
    assert "last_changed" in entity
    assert "last_updated" in entity


async def test_states_contains_created_entity(rest):
    """Created entity appears in /api/states listing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rsdl_cre_{tag}"
    await rest.set_state(eid, "42")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    entity_ids = [e["entity_id"] for e in resp.json()]
    assert eid in entity_ids


# ── Single Entity GET ───────────────────────────────────

async def test_get_single_entity_state(rest):
    """GET /api/states/<entity_id> returns single entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rsdl_single_{tag}"
    await rest.set_state(eid, "hello")

    state = await rest.get_state(eid)
    assert state["entity_id"] == eid
    assert state["state"] == "hello"


async def test_get_nonexistent_entity_404(rest):
    """GET /api/states/<nonexistent> returns 404."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.does_not_exist_ever",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Multiple Domains ────────────────────────────────────

async def test_states_multiple_domains(rest):
    """Entities from multiple domains appear in /api/states."""
    tag = uuid.uuid4().hex[:8]
    eids = [
        f"sensor.rsdl_d1_{tag}",
        f"switch.rsdl_d2_{tag}",
        f"light.rsdl_d3_{tag}",
    ]
    for eid in eids:
        await rest.set_state(eid, "on")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    all_ids = [e["entity_id"] for e in resp.json()]
    for eid in eids:
        assert eid in all_ids


async def test_states_entity_attributes_included(rest):
    """Entity attributes included in /api/states listing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rsdl_attr_{tag}"
    await rest.set_state(eid, "25.5", {"unit_of_measurement": "C"})

    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    entity = next(e for e in resp.json() if e["entity_id"] == eid)
    assert entity["attributes"]["unit_of_measurement"] == "C"
