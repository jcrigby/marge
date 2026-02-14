"""
CTS -- Attribute Preservation Tests

Tests that service calls properly preserve existing attributes
while adding new ones, and that attribute merging semantics
work correctly across domains.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Light Attribute Preservation ─────────────────────────

async def test_light_turn_on_preserves_brightness(rest):
    """Turning on a light preserves existing brightness."""
    await rest.set_state("light.ap_bright", "on", {"brightness": 150})
    await rest.call_service("light", "turn_off", {
        "entity_id": "light.ap_bright",
    })
    state = await rest.get_state("light.ap_bright")
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 150


async def test_light_turn_on_adds_brightness(rest):
    """Turning on with brightness adds it to existing attrs."""
    await rest.set_state("light.ap_add_bright", "off", {"friendly_name": "Test Light"})
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.ap_add_bright",
        "brightness": 200,
    })
    state = await rest.get_state("light.ap_add_bright")
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200
    assert state["attributes"]["friendly_name"] == "Test Light"


async def test_light_color_temp_preserved(rest):
    """color_temp attribute preserved through toggle."""
    await rest.set_state("light.ap_ct", "on", {"color_temp": 300})
    await rest.call_service("light", "toggle", {
        "entity_id": "light.ap_ct",
    })
    state = await rest.get_state("light.ap_ct")
    assert state["state"] == "off"
    assert state["attributes"]["color_temp"] == 300


async def test_light_multiple_attrs_on_turn_on(rest):
    """Multiple attributes set on turn_on."""
    await rest.set_state("light.ap_multi", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.ap_multi",
        "brightness": 255,
        "rgb_color": [0, 255, 0],
        "effect": "rainbow",
    })
    state = await rest.get_state("light.ap_multi")
    assert state["attributes"]["brightness"] == 255
    assert state["attributes"]["rgb_color"] == [0, 255, 0]
    assert state["attributes"]["effect"] == "rainbow"


# ── Climate Attribute Preservation ───────────────────────

async def test_climate_set_temp_preserves_fan_mode(rest):
    """Setting temperature preserves fan_mode."""
    await rest.set_state("climate.ap_clim", "heat", {"fan_mode": "low"})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": "climate.ap_clim",
        "temperature": 72,
    })
    state = await rest.get_state("climate.ap_clim")
    assert state["attributes"]["temperature"] == 72
    assert state["attributes"]["fan_mode"] == "low"


async def test_climate_set_fan_mode_preserves_temp(rest):
    """Setting fan_mode preserves temperature."""
    await rest.set_state("climate.ap_clim2", "heat", {"temperature": 68})
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": "climate.ap_clim2",
        "fan_mode": "high",
    })
    state = await rest.get_state("climate.ap_clim2")
    assert state["attributes"]["fan_mode"] == "high"
    assert state["attributes"]["temperature"] == 68


# ── Fan Attribute Preservation ──────────────────────────

async def test_fan_turn_on_preserves_direction(rest):
    """Turning on fan preserves direction attribute."""
    await rest.set_state("fan.ap_fan", "off", {"direction": "forward"})
    await rest.call_service("fan", "turn_on", {
        "entity_id": "fan.ap_fan",
    })
    state = await rest.get_state("fan.ap_fan")
    assert state["state"] == "on"
    assert state["attributes"]["direction"] == "forward"


async def test_fan_set_direction_preserves_percentage(rest):
    """Setting direction preserves percentage."""
    await rest.set_state("fan.ap_fan2", "on", {"percentage": 75})
    await rest.call_service("fan", "set_direction", {
        "entity_id": "fan.ap_fan2",
        "direction": "reverse",
    })
    state = await rest.get_state("fan.ap_fan2")
    assert state["attributes"]["direction"] == "reverse"
    assert state["attributes"]["percentage"] == 75


# ── Media Player Attribute Preservation ──────────────────

async def test_media_player_volume_preserves_source(rest):
    """Volume set preserves source attribute."""
    await rest.set_state("media_player.ap_mp", "playing", {"source": "HDMI 1"})
    await rest.call_service("media_player", "volume_set", {
        "entity_id": "media_player.ap_mp",
        "volume_level": 0.5,
    })
    state = await rest.get_state("media_player.ap_mp")
    assert state["attributes"]["volume_level"] == 0.5
    assert state["attributes"]["source"] == "HDMI 1"


async def test_media_player_source_preserves_volume(rest):
    """Source select preserves volume_level attribute."""
    await rest.set_state("media_player.ap_mp2", "playing", {"volume_level": 0.8})
    await rest.call_service("media_player", "select_source", {
        "entity_id": "media_player.ap_mp2",
        "source": "Bluetooth",
    })
    state = await rest.get_state("media_player.ap_mp2")
    assert state["attributes"]["source"] == "Bluetooth"
    assert state["attributes"]["volume_level"] == 0.8


# ── Cover Attribute Preservation ────────────────────────

async def test_cover_toggle_updates_position(rest):
    """Cover toggle from open→closed sets position to 0."""
    await rest.set_state("cover.ap_cov", "open", {"current_position": 100})
    await rest.call_service("cover", "toggle", {
        "entity_id": "cover.ap_cov",
    })
    state = await rest.get_state("cover.ap_cov")
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_toggle_from_closed_sets_position(rest):
    """Cover toggle from closed→open sets position to 100."""
    await rest.set_state("cover.ap_cov2", "closed", {"current_position": 0})
    await rest.call_service("cover", "toggle", {
        "entity_id": "cover.ap_cov2",
    })
    state = await rest.get_state("cover.ap_cov2")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


# ── Humidifier Attribute Preservation ───────────────────

async def test_humidifier_turn_off_preserves_humidity(rest):
    """Turning off humidifier preserves humidity setting."""
    await rest.set_state("humidifier.ap_hum", "on", {"humidity": 60})
    await rest.call_service("humidifier", "turn_off", {
        "entity_id": "humidifier.ap_hum",
    })
    state = await rest.get_state("humidifier.ap_hum")
    assert state["state"] == "off"
    assert state["attributes"]["humidity"] == 60


async def test_humidifier_set_mode_preserves_humidity(rest):
    """Setting mode preserves humidity attribute."""
    await rest.set_state("humidifier.ap_hum2", "on", {"humidity": 55})
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": "humidifier.ap_hum2",
        "mode": "eco",
    })
    state = await rest.get_state("humidifier.ap_hum2")
    assert state["attributes"]["mode"] == "eco"
    assert state["attributes"]["humidity"] == 55
