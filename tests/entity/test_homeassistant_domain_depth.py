"""
CTS -- Homeassistant Domain Service Depth Tests

Tests the homeassistant domain services: turn_on, turn_off, toggle
(generic entity control), and system stubs (restart, stop,
reload_core_config) that return no changed_states.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── homeassistant.turn_on ────────────────────────────────

async def test_ha_turn_on(rest):
    """homeassistant.turn_on sets entity to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ha_turn_on_preserves_attrs(rest):
    """homeassistant.turn_on preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_attrs_{tag}"
    await rest.set_state(eid, "off", {"icon": "mdi:fan"})
    await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["icon"] == "mdi:fan"


async def test_ha_turn_on_any_domain(rest):
    """homeassistant.turn_on works on any domain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ha_any_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── homeassistant.turn_off ───────────────────────────────

async def test_ha_turn_off(rest):
    """homeassistant.turn_off sets entity to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("homeassistant", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ha_turn_off_preserves_attrs(rest):
    """homeassistant.turn_off preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.ha_oattr_{tag}"
    await rest.set_state(eid, "on", {"percentage": 80})
    await rest.call_service("homeassistant", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["percentage"] == 80


# ── homeassistant.toggle ─────────────────────────────────

async def test_ha_toggle_on_to_off(rest):
    """homeassistant.toggle flips on to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ha_toggle_off_to_on(rest):
    """homeassistant.toggle flips off to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ha_toggle_unknown_defaults_on(rest):
    """homeassistant.toggle on non-existent entity defaults to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_tog3_{tag}"
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ha_toggle_preserves_attrs(rest):
    """homeassistant.toggle preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_toga_{tag}"
    await rest.set_state(eid, "on", {"brightness": 200})
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 200


# ── System Stubs (No Changed States) ────────────────────

async def test_ha_restart_no_changed(rest):
    """homeassistant.restart returns empty changed_states."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/restart",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json().get("changed_states", []) == []


async def test_ha_stop_no_changed(rest):
    """homeassistant.stop returns empty changed_states."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/stop",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json().get("changed_states", []) == []


async def test_ha_reload_core_config_no_changed(rest):
    """homeassistant.reload_core_config returns empty changed_states."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/reload_core_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json().get("changed_states", []) == []
