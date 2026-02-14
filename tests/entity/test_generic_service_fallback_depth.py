"""
CTS -- Generic Service Fallback Depth Tests

Tests the service registry's generic fallback handlers for turn_on,
turn_off, and toggle on arbitrary/unknown domains. Also tests that
services preserve existing attributes and that multiple entities can
be affected by a single service call.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Generic turn_on / turn_off ──────────────────────────

async def test_generic_turn_on(rest):
    """turn_on works for arbitrary domain via fallback handler."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom.gen_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("custom", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_generic_turn_off(rest):
    """turn_off works for arbitrary domain via fallback handler."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom.gen_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("custom", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_generic_toggle_on_to_off(rest):
    """toggle for arbitrary domain switches on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom.gen_tog_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("custom", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_generic_toggle_off_to_on(rest):
    """toggle for arbitrary domain switches off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom.gen_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("custom", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Attribute Preservation ──────────────────────────────

async def test_turn_on_preserves_attributes(rest):
    """turn_on preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.pres_on_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": "My Switch", "icon": "mdi:power"})
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["friendly_name"] == "My Switch"
    assert state["attributes"]["icon"] == "mdi:power"


async def test_turn_off_preserves_attributes(rest):
    """turn_off preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.pres_off_{tag}"
    await rest.set_state(eid, "on", {"friendly_name": "Test", "power": "100"})
    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["friendly_name"] == "Test"


async def test_toggle_preserves_attributes(rest):
    """toggle preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pres_tog_{tag}"
    await rest.set_state(eid, "on", {"brightness": 255})
    await rest.call_service("light", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 255


# ── Multi-Entity Service Call ───────────────────────────

async def test_service_affects_multiple_entities(rest):
    """Service call with multiple entity_ids affects all of them."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.multi_{i}_{tag}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eids},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


# ── Service on Non-Existent Entity ──────────────────────

async def test_service_on_nonexistent_creates_entity(rest):
    """Service on non-existent entity creates it with the new state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.new_svc_{tag}"
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Specific Domain Services ────────────────────────────

async def test_switch_turn_on(rest):
    """switch.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.svc_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_fan_turn_on(rest):
    """fan.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.svc_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_input_boolean_toggle(rest):
    """input_boolean.toggle flips state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.fb_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
