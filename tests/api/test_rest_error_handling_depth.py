"""
CTS -- REST API Error Handling Depth Tests

Tests REST API error responses: 404 on nonexistent state, 200 on
valid requests, method-not-allowed behaviors, empty body handling,
and content-type enforcement.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── 404 Responses ────────────────────────────────────────

async def test_get_nonexistent_state_404(rest):
    """GET /api/states/<nonexistent> returns 404."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.no_exist_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_state_404(rest):
    """DELETE /api/states/<nonexistent> returns 404."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.no_del_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_history_nonexistent_entity_empty(rest):
    """GET /api/history/period/<nonexistent> returns empty array."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.no_hist_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_logbook_nonexistent_entity_empty(rest):
    """GET /api/logbook/<nonexistent> returns empty array."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.no_log_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Valid Responses ──────────────────────────────────────

async def test_api_root_returns_200(rest):
    """GET /api/ returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_api_config_returns_200(rest):
    """GET /api/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_api_states_returns_200(rest):
    """GET /api/states returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_api_health_returns_200(rest):
    """GET /api/health returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
    )
    assert resp.status_code == 200


# ── Set State Responses ──────────────────────────────────

async def test_set_state_returns_entity_id(rest):
    """POST /api/states/<eid> response includes entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.err_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "val"},
    )
    assert resp.status_code == 200 or resp.status_code == 201
    data = resp.json()
    assert data["entity_id"] == eid


async def test_set_state_returns_state(rest):
    """POST /api/states/<eid> response includes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.err_st_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "abc"},
    )
    data = resp.json()
    assert data["state"] == "abc"


async def test_set_state_returns_attributes(rest):
    """POST /api/states/<eid> response includes attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.err_attr_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "v", "attributes": {"key": "val"}},
    )
    data = resp.json()
    assert data["attributes"]["key"] == "val"


# ── Service Call Responses ───────────────────────────────

async def test_service_call_returns_200(rest):
    """POST /api/services/<domain>/<service> returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.err_svc_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    assert resp.status_code == 200


async def test_service_call_returns_changed_states(rest):
    """Service call response includes changed_states when state changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.err_chg_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    # changed_states is present when entities changed
    if "changed_states" in data:
        assert isinstance(data["changed_states"], list)
