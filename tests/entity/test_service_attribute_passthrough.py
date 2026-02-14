"""
CTS -- Service Attribute Passthrough Tests

Verifies that service calls correctly store data fields as entity
attributes. Tests light (brightness, color_temp), climate (temperature,
fan_mode, preset_mode), fan (percentage, direction), cover (position),
media_player (volume, source, shuffle), and number/select set_value.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Light attributes ──────────────────────────────────────

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


# ── Climate attributes ─────────────────────────────────────

async def test_climate_set_temperature(rest):
    """climate.set_temperature stores temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.attr_temp_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 72,
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("temperature") == 72


async def test_climate_set_fan_mode(rest):
    """climate.set_fan_mode stores fan_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.attr_fan_{tag}"
    await rest.set_state(eid, "cool")

    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid,
        "fan_mode": "high",
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("fan_mode") == "high"


async def test_climate_set_preset_mode(rest):
    """climate.set_preset_mode stores preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.attr_preset_{tag}"
    await rest.set_state(eid, "auto")

    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": eid,
        "preset_mode": "away",
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("preset_mode") == "away"


async def test_climate_set_hvac_mode(rest):
    """climate.set_hvac_mode changes state to new mode."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.attr_hvac_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid,
        "hvac_mode": "cool",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "cool"


async def test_climate_set_swing_mode(rest):
    """climate.set_swing_mode stores swing_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.attr_swing_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": eid,
        "swing_mode": "vertical",
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("swing_mode") == "vertical"


# ── Fan attributes ──────────────────────────────────────────

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


async def test_fan_set_direction(rest):
    """fan.set_direction stores direction attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.attr_dir_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("fan", "set_direction", {
        "entity_id": eid,
        "direction": "reverse",
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("direction") == "reverse"


async def test_fan_set_percentage_zero_turns_off(rest):
    """fan.set_percentage(0) sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.attr_pct0_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid,
        "percentage": 0,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Cover attributes ──────────────────────────────────────

async def test_cover_set_position(rest):
    """cover.set_cover_position stores position and sets open/closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.attr_pos_{tag}"
    await rest.set_state(eid, "closed")

    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid,
        "position": 50,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"].get("current_position") == 50


async def test_cover_open_sets_position_100(rest):
    """cover.open_cover sets current_position to 100."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.attr_open_{tag}"
    await rest.set_state(eid, "closed")

    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"].get("current_position") == 100


async def test_cover_close_sets_position_0(rest):
    """cover.close_cover sets current_position to 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.attr_close_{tag}"
    await rest.set_state(eid, "open")

    await rest.call_service("cover", "close_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "closed"
    assert state["attributes"].get("current_position") == 0


# ── Media player attributes ──────────────────────────────

async def test_media_player_volume_set(rest):
    """media_player.volume_set stores volume_level attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.attr_vol_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid,
        "volume_level": 0.65,
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("volume_level") == 0.65


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


async def test_media_player_shuffle_set(rest):
    """media_player.shuffle_set stores shuffle attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.attr_shuf_{tag}"
    await rest.set_state(eid, "playing")

    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": eid,
        "shuffle": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("shuffle") is True
