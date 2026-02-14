"""
CTS -- HA Format Compliance Depth Tests

Tests that Marge API responses exactly match Home Assistant's expected
response formats: status codes, JSON shapes, content types, and field
names for core endpoints.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── /api/ Status ─────────────────────────────────────────

async def test_api_status_has_message(rest):
    """GET /api/ returns {message: 'API running.'}."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "API running."


# ── /api/config Format ───────────────────────────────────

async def test_config_has_required_fields(rest):
    """GET /api/config has all HA-required fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    for field in ["location_name", "latitude", "longitude", "elevation",
                  "unit_system", "time_zone", "version", "state"]:
        assert field in data, f"Missing config field: {field}"


async def test_config_unit_system_fields(rest):
    """unit_system has length, mass, temperature, volume."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    units = resp.json()["unit_system"]
    for field in ["length", "mass", "temperature", "volume"]:
        assert field in units, f"Missing unit field: {field}"


async def test_config_state_running(rest):
    """Config state is RUNNING."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.json()["state"] == "RUNNING"


# ── /api/states Format ───────────────────────────────────

async def test_state_entity_has_required_fields(rest):
    """Entity state object has all HA-required fields."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmt_{tag}"
    await rest.set_state(eid, "42", {"friendly_name": f"Test {tag}"})
    state = await rest.get_state(eid)
    for field in ["entity_id", "state", "attributes", "last_changed",
                  "last_updated", "context"]:
        assert field in state, f"Missing state field: {field}"


async def test_state_context_has_id(rest):
    """State context has id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmt_ctx_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert "id" in state["context"]


async def test_state_timestamps_are_iso(rest):
    """State timestamps are ISO 8601 formatted strings."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmt_ts_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    for ts_field in ["last_changed", "last_updated"]:
        ts = state[ts_field]
        assert isinstance(ts, str)
        assert "T" in ts  # ISO 8601 has T separator


# ── /api/events Format ──────────────────────────────────

async def test_events_list_format(rest):
    """GET /api/events returns [{event, listener_count}, ...]."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for entry in data:
        assert "event" in entry
        assert "listener_count" in entry


async def test_events_includes_state_changed(rest):
    """Events list includes state_changed."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    event_types = [e["event"] for e in resp.json()]
    assert "state_changed" in event_types


async def test_events_includes_call_service(rest):
    """Events list includes call_service."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    event_types = [e["event"] for e in resp.json()]
    assert "call_service" in event_types


# ── /api/services Format ────────────────────────────────

async def test_services_list_format(rest):
    """GET /api/services returns [{domain, services: {...}}, ...]."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    entry = data[0]
    assert "domain" in entry
    assert "services" in entry
    assert isinstance(entry["services"], dict)


async def test_services_entry_has_fields(rest):
    """Service entry has description and fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    light = next(e for e in resp.json() if e["domain"] == "light")
    turn_on = light["services"]["turn_on"]
    assert "description" in turn_on
    assert "fields" in turn_on


# ── Fire Event Response Format ───────────────────────────

async def test_fire_event_response(rest):
    """POST /api/events/:event returns {message: 'Event X fired.'}."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "fired" in data["message"].lower()


# ── Set State Response Format ────────────────────────────

async def test_set_state_returns_entity(rest):
    """POST /api/states/:eid returns the full entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmt_set_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "42", "attributes": {"unit": "W"}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == eid
    assert data["state"] == "42"
    assert data["attributes"]["unit"] == "W"


# ── Delete State Response Format ─────────────────────────

async def test_delete_state_returns_message(rest):
    """DELETE /api/states/:eid returns {message: ...}."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmt_del_{tag}"
    await rest.set_state(eid, "1")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data


async def test_delete_nonexistent_returns_404(rest):
    """DELETE /api/states/:eid for unknown entity returns 404."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.definitely_missing_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Health Response Format ───────────────────────────────

async def test_health_has_required_fields(rest):
    """GET /api/health has status, version, entity_count."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    for field in ["status", "version", "entity_count"]:
        assert field in data, f"Missing health field: {field}"


async def test_health_status_ok(rest):
    """Health status is 'ok'."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.json()["status"] == "ok"
