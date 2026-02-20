"""
CTS -- Philips Hue Integration Tests (Phase 7.2)

Tests for the Hue bridge integration endpoints:
  - GET  /api/integrations           (hue appears in list)
  - GET  /api/integrations/hue       (bridge detail / status)
  - POST /api/integrations/hue/pair  (bridge pairing)
  - POST /api/integrations/hue/add   (pre-paired bridge add)
  - Entity naming conventions for hue-created entities

Since no real Hue Bridge is reachable from the test environment,
these tests focus on API shape, validation, and structural correctness.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Integration Listing ──────────────────────────────────────

async def test_hue_appears_in_integration_list(rest):
    """GET /api/integrations includes a hue entry."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [entry["id"] for entry in data]
    assert "hue" in ids


async def test_hue_integration_entry_has_required_fields(rest):
    """Hue entry in integration list has id, name, status, device_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    hue = next(e for e in data if e["id"] == "hue")

    assert hue["name"] == "Philips Hue"
    assert hue["status"] in ("active", "inactive")
    assert isinstance(hue["device_count"], int)
    assert hue["device_count"] >= 0


async def test_hue_integration_inactive_when_no_bridges(rest):
    """With no paired bridges, hue status should be inactive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    hue = next(e for e in data if e["id"] == "hue")
    assert hue["device_count"] == 0
    assert hue["status"] == "inactive"


# ── Hue Status Endpoint ──────────────────────────────────────

async def test_hue_status_endpoint_returns_200(rest):
    """GET /api/integrations/hue returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/hue",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_hue_status_has_bridges_list(rest):
    """Hue detail response includes a bridges array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/hue",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "bridges" in data
    assert isinstance(data["bridges"], list)


async def test_hue_status_has_bridge_count(rest):
    """Hue detail response includes bridge_count field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/hue",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "bridge_count" in data
    assert isinstance(data["bridge_count"], int)


async def test_hue_status_empty_when_no_bridges(rest):
    """With no hardware, bridge_count is 0 and bridges list is empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/hue",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["bridge_count"] == 0
    assert data["bridges"] == []


# ── Hue Pair Endpoint — Validation ───────────────────────────

async def test_hue_pair_missing_ip_returns_400(rest):
    """POST /api/integrations/hue/pair without ip returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/hue/pair",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 400


async def test_hue_pair_null_ip_returns_400(rest):
    """POST with ip: null returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/hue/pair",
        headers=rest._headers(),
        json={"ip": None},
    )
    assert resp.status_code == 400


# ── Hue Add Endpoint — Validation ────────────────────────────

async def test_hue_add_missing_fields_returns_400(rest):
    """POST /api/integrations/hue/add without ip or username returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/hue/add",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 400


async def test_hue_add_missing_username_returns_400(rest):
    """POST with ip but no username returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/hue/add",
        headers=rest._headers(),
        json={"ip": "192.168.1.100"},
    )
    assert resp.status_code == 400


# ── Entity Naming Convention ─────────────────────────────────

async def test_hue_light_entity_naming(rest):
    """Hue light entities follow light.hue_{bridge}_{name} convention."""
    entity_id = "light.hue_bridge1_living_room"
    await rest.set_state(entity_id, "on", {
        "friendly_name": "Living Room",
        "integration": "hue",
        "brightness": 254,
        "color_temp": 350,
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["entity_id"] == entity_id
    assert state["state"] == "on"
    assert state["attributes"]["integration"] == "hue"
    assert state["attributes"]["brightness"] == 254


async def test_hue_sensor_entity_naming(rest):
    """Hue sensor entities follow sensor.hue_{bridge}_{name} convention."""
    entity_id = "sensor.hue_bridge1_hallway_temperature"
    await rest.set_state(entity_id, "22.3", {
        "friendly_name": "Hallway Temperature",
        "unit_of_measurement": "\u00b0C",
        "device_class": "temperature",
        "integration": "hue",
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["state"] == "22.3"
    assert state["attributes"]["device_class"] == "temperature"


async def test_hue_entities_appear_in_global_state_list(rest):
    """Hue-pattern entities appear in GET /api/states."""
    entity_id = "light.hue_cts_test_lamp"
    await rest.set_state(entity_id, "off", {"integration": "hue"})

    states = await rest.get_states()
    entity_ids = [s["entity_id"] for s in states]
    assert entity_id in entity_ids
