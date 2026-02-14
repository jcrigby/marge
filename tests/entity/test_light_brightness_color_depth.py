"""
CTS -- Light Brightness & Color Depth Tests

Tests light domain service handlers with attribute passthrough:
brightness, color_temp, rgb_color, xy_color, hs_color, effect,
transition, attribute preservation across on/off/toggle cycles.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Brightness ──────────────────────────────────────────

async def test_light_turn_on_brightness(rest):
    """light.turn_on with brightness sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_br_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 128,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 128


async def test_light_turn_on_brightness_max(rest):
    """light.turn_on with brightness=255."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_brmax_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 255,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 255


async def test_light_turn_on_brightness_min(rest):
    """light.turn_on with brightness=1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_brmin_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 1,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 1


# ── Color Temp ──────────────────────────────────────────

async def test_light_turn_on_color_temp(rest):
    """light.turn_on with color_temp sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_ct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "color_temp": 300,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["color_temp"] == 300


# ── RGB Color ───────────────────────────────────────────

async def test_light_turn_on_rgb_color(rest):
    """light.turn_on with rgb_color sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_rgb_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "rgb_color": [255, 0, 128],
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["rgb_color"] == [255, 0, 128]


# ── HS Color ────────────────────────────────────────────

async def test_light_turn_on_hs_color(rest):
    """light.turn_on with hs_color sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_hs_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "hs_color": [210.0, 80.0],
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["hs_color"] == [210.0, 80.0]


# ── Effect & Transition ────────────────────────────────

async def test_light_turn_on_effect(rest):
    """light.turn_on with effect sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_eff_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "effect": "rainbow",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["effect"] == "rainbow"


async def test_light_turn_on_transition(rest):
    """light.turn_on with transition sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_trans_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "transition": 5,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["transition"] == 5


# ── Attribute Preservation ──────────────────────────────

async def test_light_off_preserves_brightness(rest):
    """light.turn_off preserves brightness attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_offbr_{tag}"
    await rest.set_state(eid, "on", {"brightness": 200})
    await rest.call_service("light", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 200


async def test_light_toggle_preserves_attrs(rest):
    """light.toggle preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_togattr_{tag}"
    await rest.set_state(eid, "on", {"brightness": 150, "color_temp": 350})
    await rest.call_service("light", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 150
    assert state["attributes"]["color_temp"] == 350


# ── Multi-attribute ─────────────────────────────────────

async def test_light_turn_on_multiple_attrs(rest):
    """light.turn_on with brightness + color_temp together."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_multi_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 200,
        "color_temp": 400,
        "transition": 2,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200
    assert state["attributes"]["color_temp"] == 400
    assert state["attributes"]["transition"] == 2


# ── Full Lifecycle ──────────────────────────────────────

async def test_light_full_lifecycle(rest):
    """Light: off → on(br=100) → on(br=255,ct=300) → off → toggle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbcd_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 100,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 100

    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 255, "color_temp": 300,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 255
    assert state["attributes"]["color_temp"] == 300

    await rest.call_service("light", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"

    await rest.call_service("light", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
