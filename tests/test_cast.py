"""
CTS -- Google Cast Integration Tests (Phase 7.3)

Tests for the Google Cast integration endpoints:
  - GET  /api/integrations           (cast appears in list)
  - GET  /api/integrations/cast      (device detail / status)
  - POST /api/integrations/cast/discover  (manual device add)
  - Entity naming conventions for cast-created entities

Since no real Cast hardware is reachable from the test environment,
these tests focus on API shape, validation, and structural correctness.
"""

import pytest

pytestmark = pytest.mark.asyncio


# -- Integration Listing --------------------------------------------------

async def test_cast_appears_in_integration_list(rest):
    """GET /api/integrations includes a cast entry."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [entry["id"] for entry in data]
    assert "cast" in ids


async def test_cast_integration_entry_has_required_fields(rest):
    """Cast entry in integration list has id, name, status, device_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    cast = next(e for e in data if e["id"] == "cast")

    assert cast["name"] == "Google Cast"
    assert cast["status"] in ("active", "inactive")
    assert isinstance(cast["device_count"], int)
    assert cast["device_count"] >= 0


async def test_cast_integration_inactive_when_no_devices(rest):
    """With no discovered devices, cast status should be inactive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    cast = next(e for e in data if e["id"] == "cast")
    assert cast["device_count"] == 0
    assert cast["status"] == "inactive"


# -- Cast Status Endpoint -------------------------------------------------

async def test_cast_status_endpoint_returns_200(rest):
    """GET /api/integrations/cast returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/cast",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_cast_status_has_device_count(rest):
    """Cast detail response includes device_count field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/cast",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "device_count" in data
    assert isinstance(data["device_count"], int)


async def test_cast_status_has_devices_list(rest):
    """Cast detail response includes a devices array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/cast",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "devices" in data
    assert isinstance(data["devices"], list)


async def test_cast_status_empty_when_no_devices(rest):
    """With no hardware, device_count is 0 and devices list is empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/cast",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == 0
    assert data["devices"] == []


async def test_cast_status_device_count_matches_devices_length(rest):
    """device_count should equal len(devices)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/cast",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == len(data["devices"])


# -- Cast Discover Endpoint -- Validation ----------------------------------

async def test_cast_discover_missing_ip_returns_400(rest):
    """POST /api/integrations/cast/discover without ip field returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/cast/discover",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 400


async def test_cast_discover_null_ip_returns_400(rest):
    """POST with ip: null returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/cast/discover",
        headers=rest._headers(),
        json={"ip": None},
    )
    assert resp.status_code == 400


async def test_cast_discover_numeric_ip_returns_400(rest):
    """POST with ip as a number (not string) returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/cast/discover",
        headers=rest._headers(),
        json={"ip": 12345},
    )
    assert resp.status_code == 400


# -- Entity Naming Convention ----------------------------------------------

async def test_cast_media_player_entity_naming(rest):
    """Cast media_player entities follow media_player.cast_{name} convention."""
    entity_id = "media_player.cast_living_room_tv"
    await rest.set_state(entity_id, "idle", {
        "friendly_name": "Living Room TV",
        "integration": "cast",
        "supported_features": 21437,
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["entity_id"] == entity_id
    assert state["state"] == "idle"
    assert state["attributes"]["integration"] == "cast"


async def test_cast_entities_appear_in_global_state_list(rest):
    """Cast-pattern entities appear in GET /api/states."""
    entity_id = "media_player.cast_cts_test_speaker"
    await rest.set_state(entity_id, "off", {"integration": "cast"})

    states = await rest.get_states()
    entity_ids = [s["entity_id"] for s in states]
    assert entity_id in entity_ids


async def test_cast_entity_services_work(rest):
    """Standard media_player services work on cast-named entities."""
    entity_id = "media_player.cast_cts_svc_test"
    await rest.set_state(entity_id, "idle", {"integration": "cast"})

    await rest.call_service("media_player", "turn_on", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"

    await rest.call_service("media_player", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"
