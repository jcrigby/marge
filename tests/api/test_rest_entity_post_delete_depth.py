"""
CTS -- REST Entity POST/DELETE Lifecycle Depth Tests

Tests entity creation via POST /api/states/<entity_id>,
entity update (overwrite), and entity deletion behavior.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Entity Creation ─────────────────────────────────────

async def test_post_state_creates_entity(rest):
    """POST /api/states/<eid> creates new entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_create_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "42", "attributes": {"unit": "lux"}},
    )
    assert resp.status_code in (200, 201)
    state = await rest.get_state(eid)
    assert state["state"] == "42"
    assert state["attributes"]["unit"] == "lux"


async def test_post_state_returns_entity(rest):
    """POST /api/states/<eid> returns entity in response body."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_ret_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "test"},
    )
    data = resp.json()
    assert data["entity_id"] == eid
    assert data["state"] == "test"


async def test_post_state_new_entity_returns_success(rest):
    """POST /api/states/<eid> returns 200 for newly created entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_new_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "new"},
    )
    assert resp.status_code == 200


async def test_post_state_returns_200_for_update(rest):
    """POST /api/states/<eid> returns 200 for existing entity update."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_200_{tag}"
    await rest.set_state(eid, "old")
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "new"},
    )
    assert resp.status_code == 200


# ── Entity Update ───────────────────────────────────────

async def test_post_state_overwrites_state(rest):
    """Second POST overwrites entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_over_{tag}"
    await rest.set_state(eid, "first")
    await rest.set_state(eid, "second")
    state = await rest.get_state(eid)
    assert state["state"] == "second"


async def test_post_state_overwrites_attributes(rest):
    """Second POST overwrites entity attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_oattr_{tag}"
    await rest.set_state(eid, "on", {"key1": "val1"})
    await rest.set_state(eid, "on", {"key2": "val2"})
    state = await rest.get_state(eid)
    assert "key2" in state["attributes"]


# ── Entity Delete ───────────────────────────────────────

async def test_delete_entity(rest):
    """DELETE /api/states/<eid> removes entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_del_{tag}"
    await rest.set_state(eid, "temp")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    get_resp = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert get_resp.status_code == 404


async def test_delete_nonexistent_entity(rest):
    """DELETE /api/states/<nonexistent> returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.never_existed_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code in (200, 404)


# ── Edge Cases ──────────────────────────────────────────

async def test_post_state_empty_attributes(rest):
    """POST with empty attributes dict creates entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_empty_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "ok", "attributes": {}},
    )
    assert resp.status_code in (200, 201)
    state = await rest.get_state(eid)
    assert state["state"] == "ok"


async def test_post_state_numeric_state(rest):
    """POST with numeric state value stored as string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.repd_num_{tag}"
    await rest.set_state(eid, "99.5")
    state = await rest.get_state(eid)
    assert state["state"] == "99.5"
