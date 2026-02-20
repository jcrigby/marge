"""
CTS -- Matter Integration Tests (Phase 7.5)

Tests for the Matter sidecar integration endpoints:
  - GET  /api/integrations           (matter appears in list)
  - GET  /api/integrations/matter    (sidecar detail / status)
  - Entity naming conventions for matter-created entities

Since no python-matter-server sidecar is running in the test environment,
these tests focus on API shape, validation, and structural correctness.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# -- Integration Listing --------------------------------------------------

async def test_matter_appears_in_integration_list(rest):
    """GET /api/integrations includes a matter entry."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [entry["id"] for entry in data]
    assert "matter" in ids


async def test_matter_integration_entry_has_required_fields(rest):
    """Matter entry in integration list has id, name, status, device_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    matter = next(e for e in data if e["id"] == "matter")

    assert matter["name"] == "Matter"
    assert matter["status"] in ("active", "inactive", "connecting", "disconnected")
    assert isinstance(matter["device_count"], int)
    assert matter["device_count"] >= 0


async def test_matter_integration_inactive_when_no_sidecar(rest):
    """With no sidecar running, matter status should be inactive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    matter = next(e for e in data if e["id"] == "matter")
    assert matter["device_count"] == 0
    assert matter["status"] == "inactive"


# -- Matter Status Endpoint -----------------------------------------------

async def test_matter_status_endpoint_returns_200(rest):
    """GET /api/integrations/matter returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_matter_status_has_device_count(rest):
    """Matter detail response includes device_count field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "device_count" in data
    assert isinstance(data["device_count"], int)


async def test_matter_status_has_devices_list(rest):
    """Matter detail response includes a devices array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "devices" in data
    assert isinstance(data["devices"], list)


async def test_matter_status_has_status_field(rest):
    """Matter detail response includes a status field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("connected", "connecting", "disconnected", "not_running", "not_configured")


async def test_matter_status_has_server_version(rest):
    """Matter detail response includes server_version field (may be null)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "server_version" in data
    # With no sidecar, server_version should be null
    assert data["server_version"] is None


async def test_matter_status_empty_when_no_sidecar(rest):
    """With no sidecar, device_count is 0 and devices list is empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == 0
    assert data["devices"] == []


async def test_matter_status_device_count_matches_devices_length(rest):
    """device_count should equal len(devices)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == len(data["devices"])


async def test_matter_status_via_alias_path(rest):
    """GET /api/integrations/matter/status also works (alias)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/matter/status",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "device_count" in data


# -- Entity Naming Convention ----------------------------------------------

async def test_matter_light_entity_naming(rest):
    """Matter light entities follow light.matter_{name} convention."""
    entity_id = "light.matter_kitchen_light"
    await rest.set_state(entity_id, "on", {
        "friendly_name": "Kitchen Light",
        "integration": "matter",
        "brightness": 200,
        "vendor": "IKEA",
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["entity_id"] == entity_id
    assert state["state"] == "on"
    assert state["attributes"]["integration"] == "matter"
    assert state["attributes"]["brightness"] == 200


async def test_matter_lock_entity_naming(rest):
    """Matter lock entities follow lock.matter_{name} convention."""
    entity_id = "lock.matter_front_door"
    await rest.set_state(entity_id, "locked", {
        "friendly_name": "Front Door",
        "integration": "matter",
        "vendor": "Yale",
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["state"] == "locked"
    assert state["attributes"]["integration"] == "matter"


async def test_matter_climate_entity_naming(rest):
    """Matter climate entities follow climate.matter_{name} convention."""
    entity_id = "climate.matter_living_room_thermostat"
    await rest.set_state(entity_id, "heat", {
        "friendly_name": "Living Room Thermostat",
        "integration": "matter",
        "current_temperature": 21.5,
        "temperature": 22.0,
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["state"] == "heat"
    assert state["attributes"]["current_temperature"] == 21.5


async def test_matter_entities_appear_in_global_state_list(rest):
    """Matter-pattern entities appear in GET /api/states."""
    entity_id = "switch.matter_cts_test_plug"
    await rest.set_state(entity_id, "off", {"integration": "matter"})

    states = await rest.get_states()
    entity_ids = [s["entity_id"] for s in states]
    assert entity_id in entity_ids


async def test_matter_entity_services_work(rest):
    """Standard lock services work on matter-named entities."""
    entity_id = "lock.matter_cts_svc_test"
    await rest.set_state(entity_id, "unlocked", {"integration": "matter"})

    await rest.call_service("lock", "lock", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "locked"

    await rest.call_service("lock", "unlock", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "unlocked"
