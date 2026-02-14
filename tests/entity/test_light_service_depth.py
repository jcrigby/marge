"""
CTS -- Light Service Handler Depth Tests

Tests light domain service handlers with attribute passthrough:
brightness, color_temp, rgb_color, xy_color, hs_color, effect,
transition, toggle, and attribute preservation.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_light_turn_on_brightness(rest):
    """turn_on with brightness stores attribute."""
    await rest.set_state("light.depth_bright", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_bright",
        "brightness": 200,
    })
    state = await rest.get_state("light.depth_bright")
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_light_turn_on_color_temp(rest):
    """turn_on with color_temp stores attribute."""
    await rest.set_state("light.depth_ct", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_ct",
        "color_temp": 370,
    })
    state = await rest.get_state("light.depth_ct")
    assert state["state"] == "on"
    assert state["attributes"]["color_temp"] == 370


async def test_light_turn_on_rgb_color(rest):
    """turn_on with rgb_color stores attribute."""
    await rest.set_state("light.depth_rgb", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_rgb",
        "rgb_color": [255, 128, 0],
    })
    state = await rest.get_state("light.depth_rgb")
    assert state["state"] == "on"
    assert state["attributes"]["rgb_color"] == [255, 128, 0]


async def test_light_turn_on_xy_color(rest):
    """turn_on with xy_color stores attribute."""
    await rest.set_state("light.depth_xy", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_xy",
        "xy_color": [0.3, 0.5],
    })
    state = await rest.get_state("light.depth_xy")
    assert state["state"] == "on"
    assert state["attributes"]["xy_color"] == [0.3, 0.5]


async def test_light_turn_on_hs_color(rest):
    """turn_on with hs_color stores attribute."""
    await rest.set_state("light.depth_hs", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_hs",
        "hs_color": [30, 100],
    })
    state = await rest.get_state("light.depth_hs")
    assert state["state"] == "on"
    assert state["attributes"]["hs_color"] == [30, 100]


async def test_light_turn_on_effect(rest):
    """turn_on with effect stores attribute."""
    await rest.set_state("light.depth_eff", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_eff",
        "effect": "rainbow",
    })
    state = await rest.get_state("light.depth_eff")
    assert state["state"] == "on"
    assert state["attributes"]["effect"] == "rainbow"


async def test_light_turn_on_transition(rest):
    """turn_on with transition stores attribute."""
    await rest.set_state("light.depth_trans", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_trans",
        "transition": 3,
    })
    state = await rest.get_state("light.depth_trans")
    assert state["state"] == "on"
    assert state["attributes"]["transition"] == 3


async def test_light_turn_on_multiple_attrs(rest):
    """turn_on with multiple attributes stores all."""
    await rest.set_state("light.depth_multi", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_multi",
        "brightness": 128,
        "color_temp": 400,
        "transition": 2,
    })
    state = await rest.get_state("light.depth_multi")
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 128
    assert state["attributes"]["color_temp"] == 400
    assert state["attributes"]["transition"] == 2


async def test_light_turn_off_preserves_attrs(rest):
    """turn_off preserves existing attributes."""
    await rest.set_state("light.depth_offpres", "on", {"brightness": 200})
    await rest.call_service("light", "turn_off", {"entity_id": "light.depth_offpres"})
    state = await rest.get_state("light.depth_offpres")
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 200


async def test_light_toggle_on_to_off(rest):
    """light toggle from on to off."""
    await rest.set_state("light.depth_ltog1", "on")
    await rest.call_service("light", "toggle", {"entity_id": "light.depth_ltog1"})
    state = await rest.get_state("light.depth_ltog1")
    assert state["state"] == "off"


async def test_light_toggle_off_to_on(rest):
    """light toggle from off to on."""
    await rest.set_state("light.depth_ltog2", "off")
    await rest.call_service("light", "toggle", {"entity_id": "light.depth_ltog2"})
    state = await rest.get_state("light.depth_ltog2")
    assert state["state"] == "on"


async def test_light_turn_on_overwrites_previous_attrs(rest):
    """Second turn_on overwrites attributes from first."""
    await rest.set_state("light.depth_over", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_over",
        "brightness": 100,
    })
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.depth_over",
        "brightness": 255,
    })
    state = await rest.get_state("light.depth_over")
    assert state["attributes"]["brightness"] == 255
