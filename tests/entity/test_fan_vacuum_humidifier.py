"""
CTS -- Fan, Vacuum, Humidifier Service Handler Depth Tests

Tests fan (percentage, direction, preset_mode), vacuum (start, stop,
pause, return_to_base), and humidifier (humidity, mode, toggle) services.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Fan ──────────────────────────────────────────────────

async def test_fan_turn_on_with_percentage(rest):
    """fan turn_on with percentage stores attribute."""
    await rest.set_state("fan.depth_pct", "off")
    await rest.call_service("fan", "turn_on", {
        "entity_id": "fan.depth_pct",
        "percentage": 75,
    })
    state = await rest.get_state("fan.depth_pct")
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75


async def test_fan_set_percentage_zero(rest):
    """fan set_percentage to 0 sets state to off."""
    await rest.set_state("fan.depth_pct0", "on")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": "fan.depth_pct0",
        "percentage": 0,
    })
    state = await rest.get_state("fan.depth_pct0")
    assert state["state"] == "off"


async def test_fan_set_percentage_nonzero(rest):
    """fan set_percentage > 0 sets state to on."""
    await rest.set_state("fan.depth_pctn", "off")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": "fan.depth_pctn",
        "percentage": 50,
    })
    state = await rest.get_state("fan.depth_pctn")
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 50


async def test_fan_set_direction(rest):
    """fan set_direction stores direction attribute."""
    await rest.set_state("fan.depth_dir", "on")
    await rest.call_service("fan", "set_direction", {
        "entity_id": "fan.depth_dir",
        "direction": "reverse",
    })
    state = await rest.get_state("fan.depth_dir")
    assert state["attributes"]["direction"] == "reverse"


async def test_fan_set_preset_mode(rest):
    """fan set_preset_mode stores preset_mode attribute."""
    await rest.set_state("fan.depth_pmode", "on")
    await rest.call_service("fan", "set_preset_mode", {
        "entity_id": "fan.depth_pmode",
        "preset_mode": "sleep",
    })
    state = await rest.get_state("fan.depth_pmode")
    assert state["attributes"]["preset_mode"] == "sleep"


async def test_fan_toggle_on_to_off(rest):
    """fan toggle from on to off."""
    await rest.set_state("fan.depth_ftog", "on")
    await rest.call_service("fan", "toggle", {"entity_id": "fan.depth_ftog"})
    state = await rest.get_state("fan.depth_ftog")
    assert state["state"] == "off"


# ── Vacuum ───────────────────────────────────────────────

async def test_vacuum_start(rest):
    """vacuum start sets state to cleaning."""
    await rest.set_state("vacuum.depth_vstart", "idle")
    await rest.call_service("vacuum", "start", {"entity_id": "vacuum.depth_vstart"})
    state = await rest.get_state("vacuum.depth_vstart")
    assert state["state"] == "cleaning"


async def test_vacuum_stop(rest):
    """vacuum stop sets state to idle."""
    await rest.set_state("vacuum.depth_vstop", "cleaning")
    await rest.call_service("vacuum", "stop", {"entity_id": "vacuum.depth_vstop"})
    state = await rest.get_state("vacuum.depth_vstop")
    assert state["state"] == "idle"


async def test_vacuum_pause(rest):
    """vacuum pause sets state to paused."""
    await rest.set_state("vacuum.depth_vpause", "cleaning")
    await rest.call_service("vacuum", "pause", {"entity_id": "vacuum.depth_vpause"})
    state = await rest.get_state("vacuum.depth_vpause")
    assert state["state"] == "paused"


async def test_vacuum_return_to_base(rest):
    """vacuum return_to_base sets state to returning."""
    await rest.set_state("vacuum.depth_vret", "cleaning")
    await rest.call_service("vacuum", "return_to_base", {"entity_id": "vacuum.depth_vret"})
    state = await rest.get_state("vacuum.depth_vret")
    assert state["state"] == "returning"


# ── Humidifier ───────────────────────────────────────────

async def test_humidifier_turn_on(rest):
    """humidifier turn_on sets state to on."""
    await rest.set_state("humidifier.depth_hon", "off")
    await rest.call_service("humidifier", "turn_on", {"entity_id": "humidifier.depth_hon"})
    state = await rest.get_state("humidifier.depth_hon")
    assert state["state"] == "on"


async def test_humidifier_turn_off(rest):
    """humidifier turn_off sets state to off."""
    await rest.set_state("humidifier.depth_hoff", "on")
    await rest.call_service("humidifier", "turn_off", {"entity_id": "humidifier.depth_hoff"})
    state = await rest.get_state("humidifier.depth_hoff")
    assert state["state"] == "off"


async def test_humidifier_toggle(rest):
    """humidifier toggle from on to off."""
    await rest.set_state("humidifier.depth_htog", "on")
    await rest.call_service("humidifier", "toggle", {"entity_id": "humidifier.depth_htog"})
    state = await rest.get_state("humidifier.depth_htog")
    assert state["state"] == "off"


async def test_humidifier_set_humidity(rest):
    """humidifier set_humidity stores humidity attribute."""
    await rest.set_state("humidifier.depth_hum", "on")
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": "humidifier.depth_hum",
        "humidity": 45,
    })
    state = await rest.get_state("humidifier.depth_hum")
    assert state["attributes"]["humidity"] == 45


async def test_humidifier_set_mode(rest):
    """humidifier set_mode stores mode attribute."""
    await rest.set_state("humidifier.depth_hmode", "on")
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": "humidifier.depth_hmode",
        "mode": "eco",
    })
    state = await rest.get_state("humidifier.depth_hmode")
    assert state["attributes"]["mode"] == "eco"
