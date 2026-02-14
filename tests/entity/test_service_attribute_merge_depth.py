"""
CTS -- Service Attribute Merge Depth Tests

Tests that service calls correctly merge service_data into entity
attributes: brightness on turn_on, temperature on set_temperature,
volume_level on volume_set, etc. Verifies existing attributes are
preserved and new ones are added.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Light Brightness ──────────────────────────────────────

async def test_light_turn_on_with_brightness(rest):
    """light.turn_on with brightness sets brightness attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.attr_br_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 200,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_light_turn_on_with_color_temp(rest):
    """light.turn_on with color_temp sets color_temp attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.attr_ct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "color_temp": 350,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["color_temp"] == 350


async def test_light_attributes_preserved_on_toggle(rest):
    """Toggling light preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.attr_tog_{tag}"
    await rest.set_state(eid, "on", {"brightness": 150, "friendly_name": "Desk"})
    await rest.call_service("light", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 150
    assert state["attributes"]["friendly_name"] == "Desk"


# ── Climate Temperature ───────────────────────────────────

async def test_climate_temp_attribute_merge(rest):
    """climate.set_temperature merges temperature into attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.attr_tmp_{tag}"
    await rest.set_state(eid, "heat", {"fan_mode": "auto"})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 72,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72
    assert state["attributes"]["fan_mode"] == "auto"


async def test_climate_fan_mode_preserves_temp(rest):
    """climate.set_fan_mode preserves temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.attr_fm_{tag}"
    await rest.set_state(eid, "cool", {"temperature": 68})
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid,
        "fan_mode": "high",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["fan_mode"] == "high"
    assert state["attributes"]["temperature"] == 68


# ── Media Player Volume ───────────────────────────────────

async def test_media_player_volume_merge(rest):
    """media_player.volume_set merges volume_level."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.attr_vol_{tag}"
    await rest.set_state(eid, "playing", {"media_title": "Song"})
    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid,
        "volume_level": 0.7,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.7
    assert state["attributes"]["media_title"] == "Song"


# ── Cover Position ────────────────────────────────────────

async def test_cover_position_merge(rest):
    """cover.set_cover_position merges current_position."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.attr_pos_{tag}"
    await rest.set_state(eid, "open", {"friendly_name": "Blinds"})
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid,
        "position": 75,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["current_position"] == 75
    assert state["attributes"]["friendly_name"] == "Blinds"


# ── Fan Percentage ────────────────────────────────────────

async def test_fan_percentage_merge(rest):
    """fan.set_percentage merges percentage attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.attr_pct_{tag}"
    await rest.set_state(eid, "on", {"preset_mode": "auto"})
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid,
        "percentage": 50,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["percentage"] == 50
    assert state["attributes"]["preset_mode"] == "auto"


# ── Generic Turn On Preserves Attributes ──────────────────

async def test_generic_turn_on_preserves_attrs(rest):
    """Generic turn_on preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.attr_gen_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": "Pump", "icon": "mdi:water"})
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["friendly_name"] == "Pump"
    assert state["attributes"]["icon"] == "mdi:water"


async def test_generic_turn_off_preserves_attrs(rest):
    """Generic turn_off preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.attr_off_{tag}"
    await rest.set_state(eid, "on", {"friendly_name": "Heater", "wattage": 1500})
    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["friendly_name"] == "Heater"
    assert state["attributes"]["wattage"] == 1500
