"""
CTS -- Light Attribute Passthrough Depth Tests

Tests that light.turn_on correctly passes through all supported
attributes: brightness, color_temp, rgb_color, xy_color, hs_color,
effect, transition. Verifies attribute preservation across service
calls and toggle behavior.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── brightness ────────────────────────────────────────────

async def test_light_turn_on_brightness(rest):
    """light.turn_on with brightness sets brightness attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_br_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 128,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 128


async def test_light_brightness_update(rest):
    """Calling turn_on again updates brightness."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_bru_{tag}"
    await rest.set_state(eid, "on", {"brightness": 100})
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 255,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 255


# ── color_temp ────────────────────────────────────────────

async def test_light_turn_on_color_temp(rest):
    """light.turn_on with color_temp sets color_temp attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_ct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "color_temp": 370,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["color_temp"] == 370


# ── rgb_color ─────────────────────────────────────────────

async def test_light_turn_on_rgb_color(rest):
    """light.turn_on with rgb_color sets rgb_color attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_rgb_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "rgb_color": [255, 0, 128],
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["rgb_color"] == [255, 0, 128]


# ── xy_color ──────────────────────────────────────────────

async def test_light_turn_on_xy_color(rest):
    """light.turn_on with xy_color sets xy_color attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_xy_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "xy_color": [0.3, 0.3],
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["xy_color"] == [0.3, 0.3]


# ── hs_color ──────────────────────────────────────────────

async def test_light_turn_on_hs_color(rest):
    """light.turn_on with hs_color sets hs_color attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_hs_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "hs_color": [240, 100],
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["hs_color"] == [240, 100]


# ── effect ────────────────────────────────────────────────

async def test_light_turn_on_effect(rest):
    """light.turn_on with effect sets effect attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_eff_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "effect": "rainbow",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["effect"] == "rainbow"


# ── transition ────────────────────────────────────────────

async def test_light_turn_on_transition(rest):
    """light.turn_on with transition sets transition attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_trans_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "transition": 2,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["transition"] == 2


# ── Multiple attributes ──────────────────────────────────

async def test_light_turn_on_multiple_attrs(rest):
    """light.turn_on with brightness + color_temp sets both."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_multi_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 200,
        "color_temp": 250,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200
    assert state["attributes"]["color_temp"] == 250


async def test_light_turn_on_brightness_rgb(rest):
    """light.turn_on with brightness + rgb_color sets both."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_brgb_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 150,
        "rgb_color": [0, 255, 0],
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 150
    assert state["attributes"]["rgb_color"] == [0, 255, 0]


# ── Attribute preservation across calls ───────────────────

async def test_light_turn_off_preserves_brightness(rest):
    """light.turn_off preserves brightness from previous on state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_pres_{tag}"
    await rest.set_state(eid, "on", {"brightness": 200, "friendly_name": "Lamp"})
    await rest.call_service("light", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 200
    assert state["attributes"]["friendly_name"] == "Lamp"


async def test_light_turn_on_preserves_friendly_name(rest):
    """light.turn_on preserves existing friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_fn_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": "Kitchen Light"})
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 100,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == "Kitchen Light"
    assert state["attributes"]["brightness"] == 100


# ── Toggle ────────────────────────────────────────────────

async def test_light_toggle_on_to_off(rest):
    """light.toggle: on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_tog_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("light", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_light_toggle_off_to_on(rest):
    """light.toggle: off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_light_toggle_preserves_attrs(rest):
    """light.toggle preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lt_togp_{tag}"
    await rest.set_state(eid, "on", {"brightness": 180})
    await rest.call_service("light", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 180
