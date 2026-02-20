"""
CTS -- Sonos Integration Tests (Phase 7.4)

Tests for the Sonos integration endpoints:
  - GET  /api/integrations           (sonos appears in list)
  - GET  /api/integrations/sonos     (device detail / status)
  - POST /api/integrations/sonos/discover  (manual device add)
  - Entity naming conventions for sonos-created entities

Since no real Sonos hardware is reachable from the test environment,
these tests focus on API shape, validation, and structural correctness.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# -- Integration Listing --------------------------------------------------

async def test_sonos_appears_in_integration_list(rest):
    """GET /api/integrations includes a sonos entry."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [entry["id"] for entry in data]
    assert "sonos" in ids


async def test_sonos_integration_entry_has_required_fields(rest):
    """Sonos entry in integration list has id, name, status, device_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    sonos = next(e for e in data if e["id"] == "sonos")

    assert sonos["name"] == "Sonos"
    assert sonos["status"] in ("active", "inactive")
    assert isinstance(sonos["device_count"], int)
    assert sonos["device_count"] >= 0


async def test_sonos_integration_inactive_when_no_devices(rest):
    """With no discovered devices, sonos status should be inactive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations",
        headers=rest._headers(),
    )
    data = resp.json()
    sonos = next(e for e in data if e["id"] == "sonos")
    assert sonos["device_count"] == 0
    assert sonos["status"] == "inactive"


# -- Sonos Status Endpoint ------------------------------------------------

async def test_sonos_status_endpoint_returns_200(rest):
    """GET /api/integrations/sonos returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/sonos",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_sonos_status_has_device_count(rest):
    """Sonos detail response includes device_count field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/sonos",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "device_count" in data
    assert isinstance(data["device_count"], int)


async def test_sonos_status_has_devices_list(rest):
    """Sonos detail response includes a devices array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/sonos",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "devices" in data
    assert isinstance(data["devices"], list)


async def test_sonos_status_empty_when_no_devices(rest):
    """With no hardware, device_count is 0 and devices list is empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/sonos",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == 0
    assert data["devices"] == []


async def test_sonos_status_device_count_matches_devices_length(rest):
    """device_count should equal len(devices)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/integrations/sonos",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["device_count"] == len(data["devices"])


# -- Sonos Discover Endpoint -- Validation ---------------------------------

async def test_sonos_discover_missing_ip_returns_400(rest):
    """POST /api/integrations/sonos/discover without ip field returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/sonos/discover",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 400


async def test_sonos_discover_null_ip_returns_400(rest):
    """POST with ip: null returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/sonos/discover",
        headers=rest._headers(),
        json={"ip": None},
    )
    assert resp.status_code == 400


async def test_sonos_discover_numeric_ip_returns_400(rest):
    """POST with ip as a number (not string) returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/integrations/sonos/discover",
        headers=rest._headers(),
        json={"ip": 12345},
    )
    assert resp.status_code == 400


# -- Entity Naming Convention ----------------------------------------------

async def test_sonos_media_player_entity_naming(rest):
    """Sonos media_player entities follow media_player.sonos_{name} convention."""
    entity_id = "media_player.sonos_living_room"
    await rest.set_state(entity_id, "idle", {
        "friendly_name": "Living Room",
        "integration": "sonos",
        "volume_level": 0.35,
        "is_volume_muted": False,
        "source": "TV",
    })

    state = await rest.get_state(entity_id)
    assert state is not None
    assert state["entity_id"] == entity_id
    assert state["state"] == "idle"
    assert state["attributes"]["integration"] == "sonos"
    assert state["attributes"]["volume_level"] == 0.35


async def test_sonos_entities_appear_in_global_state_list(rest):
    """Sonos-pattern entities appear in GET /api/states."""
    entity_id = "media_player.sonos_cts_test_speaker"
    await rest.set_state(entity_id, "paused", {"integration": "sonos"})

    states = await rest.get_states()
    entity_ids = [s["entity_id"] for s in states]
    assert entity_id in entity_ids


async def test_sonos_entity_services_work(rest):
    """Standard media_player services work on sonos-named entities."""
    entity_id = "media_player.sonos_cts_svc_test"
    await rest.set_state(entity_id, "idle", {"integration": "sonos"})

    await rest.call_service("media_player", "turn_on", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"

    await rest.call_service("media_player", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"
