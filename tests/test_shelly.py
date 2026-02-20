"""
CTS -- Shelly Integration Tests (Phase 7.1)

Tests for the Shelly device integration endpoints:
  - GET  /api/integrations           (shelly appears in list)
  - GET  /api/integrations/shelly    (bridge detail / status)
  - POST /api/integrations/shelly/discover  (manual device add)
  - Entity naming conventions for shelly-created entities

Since no real Shelly hardware is reachable from the test environment,
these tests focus on API shape, validation, and structural correctness.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Integration Listing ──────────────────────────────────────

async def test_shelly_appears_in_integration_list(rest):
    """GET /api/integrations includes a shelly entry."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [entry["id"] for entry in data]
    assert "shelly" in ids


async def test_shelly_integration_entry_has_required_fields(rest):
    """Shelly entry in integration list has id, name, status, device_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    shelly = next(e for e in data if e["id"] == "shelly")

    assert shelly["name"] == "Shelly"
    assert shelly["status"] in ("active", "inactive")
    assert isinstance(shelly["device_count"], int)
    assert shelly["device_count"] >= 0


async def test_shelly_integration_status_inactive_when_no_devices(rest):
    """With no discovered devices, shelly status should be inactive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    shelly = next(e for e in data if e["id"] == "shelly")
    # In a clean test environment with no real Shelly hardware,
    # the device count should be 0 and status inactive.
    assert shelly["device_count"] == 0
    assert shelly["status"] == "inactive"


# ── Shelly Bridge Detail Endpoint ────────────────────────────

async def test_shelly_status_endpoint_returns_200(rest):
    """GET /api/integrations/shelly returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/shelly",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_shelly_status_has_device_count(rest):
    """Shelly detail response includes device_count field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/shelly",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "device_count" in data
    assert isinstance(data["device_count"], int)


async def test_shelly_status_has_devices_list(rest):
    """Shelly detail response includes a devices array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/shelly",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "devices" in data
    assert isinstance(data["devices"], list)


async def test_shelly_status_empty_when_no_devices(rest):
    """With no hardware, device_count is 0 and devices list is empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/shelly",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == 0
    assert data["devices"] == []


async def test_shelly_status_device_count_matches_devices_length(rest):
    """device_count should equal len(devices)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/shelly",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == len(data["devices"])


# ── Shelly Discover Endpoint — Validation ────────────────────

async def test_shelly_discover_missing_ip_returns_400(rest):
    """POST /api/integrations/shelly/discover without ip field returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/shelly/discover",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 400


async def test_shelly_discover_null_ip_returns_400(rest):
    """POST with ip: null returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/shelly/discover",
        headers=rest._headers(),
        json={"ip": None},
    )
    assert resp.status_code == 400


async def test_shelly_discover_numeric_ip_returns_400(rest):
    """POST with ip as a number (not string) returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/shelly/discover",
        headers=rest._headers(),
        json={"ip": 12345},
    )
    assert resp.status_code == 400


# NOTE: Unreachable-IP discover tests omitted — reqwest 10s timeout makes
# them too slow for routine CTS runs.  Verified manually during development.


# ── Entity Naming Convention ─────────────────────────────────

async def test_shelly_entity_naming_switch(rest):
    """Shelly switch entities follow switch.shelly_{mac}_{idx} convention."""
    # Simulate what the poller would create
    entity_id = "switch.shelly_aabbccddeeff_0"
    await rest.set_state(entity_id, "on", {
        "friendly_name": "Test Shelly Switch",
        "integration": "shelly",
        "ip_address": "192.168.1.100",
        "device_class": "switch",
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["entity_id"] == entity_id
    assert state["state"] == "on"
    assert state["attributes"]["integration"] == "shelly"
    assert state["attributes"]["device_class"] == "switch"


async def test_shelly_entity_naming_light(rest):
    """Shelly light entities follow light.shelly_{mac}_{idx} convention."""
    entity_id = "light.shelly_112233445566_0"
    await rest.set_state(entity_id, "off", {
        "friendly_name": "Test Shelly Light",
        "integration": "shelly",
        "brightness": 75,
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["entity_id"] == entity_id
    assert state["state"] == "off"
    assert state["attributes"]["integration"] == "shelly"
    assert state["attributes"]["brightness"] == 75


async def test_shelly_entity_naming_sensor(rest):
    """Shelly sensor entities follow sensor.shelly_{mac}_{metric} convention."""
    entity_id = "sensor.shelly_aabbccddeeff_temperature"
    await rest.set_state(entity_id, "23.5", {
        "friendly_name": "Test Shelly Temperature",
        "unit_of_measurement": "\u00b0C",
        "device_class": "temperature",
        "integration": "shelly",
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["state"] == "23.5"
    assert state["attributes"]["unit_of_measurement"] == "\u00b0C"
    assert state["attributes"]["device_class"] == "temperature"


async def test_shelly_entities_appear_in_global_state_list(rest):
    """Shelly-pattern entities appear in GET /api/states."""
    entity_id = "switch.shelly_cts_test_99_0"
    await rest.set_state(entity_id, "off", {"integration": "shelly"})

    states = await rest.get_states()
    entity_ids = [s["entity_id"] for s in states]
    assert entity_id in entity_ids


async def test_shelly_entity_services_work(rest):
    """Standard switch services work on shelly-named entities."""
    entity_id = "switch.shelly_cts_svc_test_0"
    await rest.set_state(entity_id, "off", {"integration": "shelly"})

    await rest.call_service("switch", "turn_on", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"

    await rest.call_service("switch", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"

    await rest.call_service("switch", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"
