"""
CTS -- API Endpoint Depth Tests

Tests additional REST API endpoints and response formats:
GET /api/ status, GET /api/config, fire_event, service call
response format, entity delete, and GET /api/states list.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── API Root ────────────────────────────────────────────

async def test_api_root_message(rest):
    """GET /api/ returns message field."""
    data = await rest.get_api_status()
    assert "message" in data


# ── Config Endpoint ─────────────────────────────────────

async def test_config_has_location(rest):
    """Config has latitude and longitude."""
    data = await rest.get_config()
    assert "latitude" in data
    assert "longitude" in data
    assert isinstance(data["latitude"], (int, float))


async def test_config_has_unit_system(rest):
    """Config has unit_system with expected keys."""
    data = await rest.get_config()
    assert "unit_system" in data
    us = data["unit_system"]
    assert "length" in us
    assert "temperature" in us


async def test_config_has_timezone(rest):
    """Config has time_zone field."""
    data = await rest.get_config()
    assert "time_zone" in data
    assert len(data["time_zone"]) > 0


async def test_config_state_running(rest):
    """Config state is RUNNING."""
    data = await rest.get_config()
    assert data["state"] == "RUNNING"


# ── Fire Event ──────────────────────────────────────────

async def test_fire_event_returns_message(rest):
    """POST /api/events/:event_type returns message."""
    data = await rest.fire_event("test_event_api_depth")
    assert "message" in data


async def test_fire_event_with_data(rest):
    """Fire event with data payload succeeds."""
    data = await rest.fire_event("test_event_with_data", {
        "key1": "value1",
        "key2": 42,
    })
    assert "message" in data


# ── Service Call Response ───────────────────────────────

async def test_service_call_returns_changed(rest):
    """Service call returns changed_states."""
    await rest.set_state("light.api_depth_svc", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.api_depth_svc"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "changed_states" in data
    assert len(data["changed_states"]) > 0


async def test_service_call_changed_state_format(rest):
    """Changed state in service response has expected fields."""
    await rest.set_state("light.api_depth_fmt", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.api_depth_fmt"},
        headers=rest._headers(),
    )
    data = resp.json()
    entity = data["changed_states"][0]
    assert "entity_id" in entity
    assert "state" in entity
    assert entity["state"] == "on"


# ── Get All States ──────────────────────────────────────

async def test_get_states_returns_list(rest):
    """GET /api/states returns list."""
    states = await rest.get_states()
    assert isinstance(states, list)
    assert len(states) > 0


async def test_get_states_entry_format(rest):
    """State entries have required fields."""
    states = await rest.get_states()
    for s in states[:5]:
        assert "entity_id" in s
        assert "state" in s
        assert "attributes" in s
        assert "last_changed" in s
        assert "last_updated" in s


async def test_get_states_contains_created(rest):
    """Newly created entity appears in states list."""
    await rest.set_state("sensor.api_depth_appears", "visible")
    states = await rest.get_states()
    ids = [s["entity_id"] for s in states]
    assert "sensor.api_depth_appears" in ids


# ── Entity Delete ───────────────────────────────────────

async def test_delete_entity_removes_from_list(rest):
    """Deleted entity disappears from states list."""
    await rest.set_state("sensor.api_depth_del", "temporary")
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.api_depth_del",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state("sensor.api_depth_del")
    assert state is None


async def test_delete_entity_twice_404(rest):
    """Deleting already-deleted entity returns 404."""
    await rest.set_state("sensor.api_depth_del2", "temp")
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.api_depth_del2",
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.api_depth_del2",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Health Endpoint ─────────────────────────────────────

async def test_health_has_fields(rest):
    """Health endpoint has expected metric fields."""
    health = await rest.get_health()
    assert "entity_count" in health
    assert "memory_rss_mb" in health
    assert "uptime_seconds" in health


async def test_health_entity_count_positive(rest):
    """Health entity count is positive."""
    health = await rest.get_health()
    assert health["entity_count"] > 0


async def test_health_uptime_positive(rest):
    """Health uptime is positive."""
    health = await rest.get_health()
    assert health["uptime_seconds"] > 0
