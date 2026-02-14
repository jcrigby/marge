"""
CTS -- Homeassistant Domain Service Tests

Tests the 'homeassistant' domain services: turn_on, turn_off, toggle,
restart, stop, reload_core_config stubs.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_homeassistant_turn_on(rest):
    """homeassistant.turn_on sets entity to 'on'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_svc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_homeassistant_turn_off(rest):
    """homeassistant.turn_off sets entity to 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_off_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("homeassistant", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_homeassistant_toggle(rest):
    """homeassistant.toggle flips entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_tog_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_homeassistant_restart_stub(rest):
    """homeassistant.restart is a no-op stub (returns 200)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/restart",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_homeassistant_stop_stub(rest):
    """homeassistant.stop is a no-op stub (returns 200)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/stop",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_homeassistant_reload_core_config_stub(rest):
    """homeassistant.reload_core_config is a no-op stub (returns 200)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/reload_core_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_homeassistant_turn_on_preserves_attributes(rest):
    """homeassistant.turn_on preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_attr_{tag}"
    await rest.set_state(eid, "off", {"brightness": 200, "friendly_name": f"Test {tag}"})

    await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 200
    assert state["attributes"].get("friendly_name") == f"Test {tag}"


async def test_homeassistant_works_across_domains(rest):
    """homeassistant.turn_on works on any domain entity."""
    tag = uuid.uuid4().hex[:8]

    entities = [
        f"light.ha_cross_{tag}",
        f"switch.ha_cross_{tag}",
        f"fan.ha_cross_{tag}",
    ]
    for eid in entities:
        await rest.set_state(eid, "off")
        await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})

    for eid in entities:
        assert (await rest.get_state(eid))["state"] == "on"
