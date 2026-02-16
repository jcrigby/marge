"""
CTS -- Service Attribute Passthrough Tests

Verifies that service calls correctly store data fields as entity
attributes. Tests light (brightness, color_temp, rgb_color, multiple),
fan (percentage), and media_player (source).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# -- Light attributes --

async def test_light_brightness_stored(rest):
    """light.turn_on with brightness stores it as attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.attr_bright_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 200,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 200


async def test_light_color_temp_stored(rest):
    """light.turn_on with color_temp stores it as attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.attr_ct_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "color_temp": 370,
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("color_temp") == 370


async def test_light_rgb_color_stored(rest):
    """light.turn_on with rgb_color stores it as attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.attr_rgb_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "rgb_color": [255, 128, 0],
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("rgb_color") == [255, 128, 0]


async def test_light_multiple_attrs_at_once(rest):
    """light.turn_on with multiple attributes stores all."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.attr_multi_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 128,
        "color_temp": 300,
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("brightness") == 128
    assert state["attributes"].get("color_temp") == 300


# -- Fan attributes --

async def test_fan_percentage_stored(rest):
    """fan.turn_on with percentage stores it."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.attr_pct_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("fan", "turn_on", {
        "entity_id": eid,
        "percentage": 75,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("percentage") == 75


# -- Media player attributes --

async def test_media_player_select_source(rest):
    """media_player.select_source stores source attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.attr_src_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("media_player", "select_source", {
        "entity_id": eid,
        "source": "Spotify",
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("source") == "Spotify"
