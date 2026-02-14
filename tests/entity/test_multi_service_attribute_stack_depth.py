"""
CTS -- Multi-Service Attribute Stacking Depth Tests

Tests sequential service calls on complex domains where each call
must preserve attributes set by previous calls. Validates that
attribute merging across service invocations works correctly.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Climate Attribute Stacking ─────────────────────────────

async def test_climate_temp_then_fan_preserved(rest):
    """Setting fan_mode after temperature preserves temperature."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.stack_tf_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 72,
    })
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid, "fan_mode": "high",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72
    assert state["attributes"]["fan_mode"] == "high"


async def test_climate_four_service_stack(rest):
    """All four climate services stack attributes correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.stack_4_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 68,
    })
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid, "fan_mode": "auto",
    })
    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": eid, "preset_mode": "away",
    })
    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": eid, "swing_mode": "both",
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 68
    assert state["attributes"]["fan_mode"] == "auto"
    assert state["attributes"]["preset_mode"] == "away"
    assert state["attributes"]["swing_mode"] == "both"
    assert state["state"] == "heat"


async def test_climate_hvac_mode_preserves_attrs(rest):
    """Changing HVAC mode preserves temperature and fan attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.stack_hv_{tag}"
    await rest.set_state(eid, "heat", {"temperature": 72, "fan_mode": "low"})

    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "cool",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "cool"
    assert state["attributes"]["temperature"] == 72
    assert state["attributes"]["fan_mode"] == "low"


async def test_climate_temp_range_with_swing(rest):
    """Temperature range + swing mode stack correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.stack_rs_{tag}"
    await rest.set_state(eid, "heat_cool")

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "target_temp_high": 78,
        "target_temp_low": 65,
    })
    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": eid, "swing_mode": "vertical",
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["target_temp_high"] == 78
    assert state["attributes"]["target_temp_low"] == 65
    assert state["attributes"]["swing_mode"] == "vertical"


# ── Fan Attribute Stacking ─────────────────────────────────

async def test_fan_percentage_then_direction(rest):
    """Fan percentage then direction both preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.stack_pd_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("fan", "turn_on", {
        "entity_id": eid, "percentage": 75,
    })
    await rest.call_service("fan", "set_direction", {
        "entity_id": eid, "direction": "reverse",
    })

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75
    assert state["attributes"]["direction"] == "reverse"


async def test_fan_three_attr_stack(rest):
    """Fan percentage + direction + preset_mode all preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.stack_3_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("fan", "turn_on", {
        "entity_id": eid, "percentage": 50,
    })
    await rest.call_service("fan", "set_direction", {
        "entity_id": eid, "direction": "forward",
    })
    await rest.call_service("fan", "set_preset_mode", {
        "entity_id": eid, "preset_mode": "sleep",
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["percentage"] == 50
    assert state["attributes"]["direction"] == "forward"
    assert state["attributes"]["preset_mode"] == "sleep"


# ── Media Player Attribute Stacking ────────────────────────

async def test_media_player_four_attr_stack(rest):
    """Media player: source + volume + shuffle + repeat all preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.stack_4_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("media_player", "turn_on", {
        "entity_id": eid, "source": "Spotify",
    })
    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid, "volume_level": 0.6,
    })
    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": eid, "shuffle": True,
    })
    await rest.call_service("media_player", "repeat_set", {
        "entity_id": eid, "repeat": "all",
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["source"] == "Spotify"
    assert state["attributes"]["volume_level"] == 0.6
    assert state["attributes"]["shuffle"] is True
    assert state["attributes"]["repeat"] == "all"


async def test_media_player_mute_preserves_volume(rest):
    """Muting preserves existing volume_level."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.stack_mv_{tag}"
    await rest.set_state(eid, "playing")

    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid, "volume_level": 0.8,
    })
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": eid, "is_volume_muted": True,
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.8
    assert state["attributes"]["is_volume_muted"] is True


# ── Light Attribute Persistence Through Toggle ─────────────

async def test_light_brightness_survives_off_on(rest):
    """Light brightness attribute persists through turn_off → turn_on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.stack_boo_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 200, "color_temp": 350,
    })
    assert (await rest.get_state(eid))["attributes"]["brightness"] == 200

    await rest.call_service("light", "turn_off", {"entity_id": eid})
    state_off = await rest.get_state(eid)
    assert state_off["state"] == "off"
    assert state_off["attributes"]["brightness"] == 200
    assert state_off["attributes"]["color_temp"] == 350

    await rest.call_service("light", "turn_on", {"entity_id": eid})
    state_on = await rest.get_state(eid)
    assert state_on["state"] == "on"
    assert state_on["attributes"]["brightness"] == 200
    assert state_on["attributes"]["color_temp"] == 350


async def test_light_rgb_then_effect_stacked(rest):
    """Light rgb_color and effect set sequentially both preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.stack_re_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "rgb_color": [255, 0, 128],
    })
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "effect": "rainbow",
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["rgb_color"] == [255, 0, 128]
    assert state["attributes"]["effect"] == "rainbow"


# ── Cover Position Chain ───────────────────────────────────

async def test_cover_position_chain(rest):
    """Cover: open → set_position → stop preserves position."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.stack_pos_{tag}"
    await rest.set_state(eid, "closed")

    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    assert (await rest.get_state(eid))["attributes"]["current_position"] == 100

    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid, "position": 50,
    })
    assert (await rest.get_state(eid))["attributes"]["current_position"] == 50
    assert (await rest.get_state(eid))["state"] == "open"

    await rest.call_service("cover", "stop_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["current_position"] == 50
    assert state["state"] == "open"


# ── Counter Arithmetic Accumulation ────────────────────────

async def test_counter_mixed_operations(rest):
    """Counter: increment 5, decrement 2, reset — arithmetic accumulates."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.stack_arith_{tag}"
    await rest.set_state(eid, "0", {"initial": 0})

    for _ in range(5):
        await rest.call_service("counter", "increment", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "5"

    for _ in range(2):
        await rest.call_service("counter", "decrement", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "3"

    await rest.call_service("counter", "reset", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "0"


# ── Humidifier Attribute Stacking ──────────────────────────

async def test_humidifier_mode_then_humidity(rest):
    """Humidifier mode + humidity set sequentially both preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.stack_mh_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "eco",
    })
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 55,
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["mode"] == "eco"
    assert state["attributes"]["humidity"] == 55
