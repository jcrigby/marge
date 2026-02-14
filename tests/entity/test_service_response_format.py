"""
CTS -- Service Call Response Format Tests

Tests that service call responses have the correct format: changed_states
array with proper entity fields.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_service_response_has_changed_states(rest):
    """Service call response contains changed_states key."""
    await rest.set_state("light.svc_resp_1", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.svc_resp_1"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "changed_states" in data


async def test_service_response_changed_has_entity_id(rest):
    """Changed state entries have entity_id field."""
    await rest.set_state("light.svc_resp_2", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.svc_resp_2"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data["changed_states"]) > 0
    entry = data["changed_states"][0]
    assert "entity_id" in entry
    assert entry["entity_id"] == "light.svc_resp_2"


async def test_service_response_changed_has_state(rest):
    """Changed state entries have state field."""
    await rest.set_state("switch.svc_resp_3", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"entity_id": "switch.svc_resp_3"},
        headers=rest._headers(),
    )
    data = resp.json()
    entry = data["changed_states"][0]
    assert "state" in entry
    assert entry["state"] == "on"


async def test_service_response_changed_has_attributes(rest):
    """Changed state entries have attributes field."""
    await rest.set_state("light.svc_resp_4", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.svc_resp_4", "brightness": 128},
        headers=rest._headers(),
    )
    data = resp.json()
    entry = data["changed_states"][0]
    assert "attributes" in entry


async def test_service_response_changed_has_timestamps(rest):
    """Changed state entries have timestamp fields."""
    await rest.set_state("light.svc_resp_5", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.svc_resp_5"},
        headers=rest._headers(),
    )
    data = resp.json()
    entry = data["changed_states"][0]
    assert "last_changed" in entry
    assert "last_updated" in entry


async def test_service_response_changed_has_context(rest):
    """Changed state entries have context field."""
    await rest.set_state("light.svc_resp_6", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.svc_resp_6"},
        headers=rest._headers(),
    )
    data = resp.json()
    entry = data["changed_states"][0]
    assert "context" in entry
    assert "id" in entry["context"]


async def test_toggle_returns_changed_state(rest):
    """Toggle service returns the changed state."""
    await rest.set_state("switch.svc_resp_tog", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/toggle",
        json={"entity_id": "switch.svc_resp_tog"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data["changed_states"]) > 0
    assert data["changed_states"][0]["state"] == "off"


async def test_turn_off_returns_changed_state(rest):
    """Turn off service returns the changed state."""
    await rest.set_state("light.svc_resp_off", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_off",
        json={"entity_id": "light.svc_resp_off"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data["changed_states"]) > 0
    assert data["changed_states"][0]["state"] == "off"


async def test_climate_service_returns_changed(rest):
    """Climate service returns changed state with attributes."""
    await rest.set_state("climate.svc_resp_clim", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_temperature",
        json={"entity_id": "climate.svc_resp_clim", "temperature": 72},
        headers=rest._headers(),
    )
    data = resp.json()
    assert "changed_states" in data
    if len(data["changed_states"]) > 0:
        entry = data["changed_states"][0]
        assert entry["attributes"].get("temperature") == 72


async def test_lock_service_returns_changed(rest):
    """Lock service returns changed state."""
    await rest.set_state("lock.svc_resp_lock", "unlocked")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/lock/lock",
        json={"entity_id": "lock.svc_resp_lock"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data["changed_states"]) > 0
    assert data["changed_states"][0]["state"] == "locked"
