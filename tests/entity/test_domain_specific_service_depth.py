"""
CTS -- Domain-Specific Service Edge Cases Depth Tests

Tests edge cases for domain-specific service handlers: alarm arm/disarm
cycle, climate mode + temperature combined, cover position, fan speed,
and media_player play_media variants.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Alarm Control Panel Cycle ───────────────────────────

async def test_alarm_full_cycle(rest):
    """Alarm: disarmed → arm_home → arm_away → arm_night → disarm."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.fc_{tag}"
    await rest.set_state(eid, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_home"
    await rest.call_service("alarm_control_panel", "arm_away", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_away"
    await rest.call_service("alarm_control_panel", "arm_night", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_night"
    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "disarmed"


async def test_alarm_trigger(rest):
    """alarm_control_panel.trigger sets state to triggered."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.trig_{tag}"
    await rest.set_state(eid, "armed_home")
    await rest.call_service("alarm_control_panel", "trigger", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "triggered"


# ── Climate Combined ───────────────────────────────────

async def test_climate_set_hvac_mode(rest):
    """climate.set_hvac_mode changes state to mode value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("climate", "set_hvac_mode", {"entity_id": eid, "hvac_mode": "cool"})
    assert (await rest.get_state(eid))["state"] == "cool"


async def test_climate_set_preset_mode(rest):
    """climate.set_preset_mode sets preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.preset_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": eid,
        "preset_mode": "away",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "away"


async def test_climate_set_fan_mode(rest):
    """climate.set_fan_mode sets fan_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.fan_{tag}"
    await rest.set_state(eid, "cool")
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid,
        "fan_mode": "high",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["fan_mode"] == "high"


# ── Cover Position ─────────────────────────────────────

async def test_cover_set_position(rest):
    """cover.set_cover_position sets position attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.pos_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid,
        "position": 50,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["current_position"] == 50


async def test_cover_close_open_cycle(rest):
    """cover: close → open cycle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cyc_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("cover", "close_cover", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"
    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"


# ── Fan Speed ──────────────────────────────────────────

async def test_fan_set_percentage(rest):
    """fan.set_percentage sets percentage attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.pct_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid,
        "percentage": 75,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["percentage"] == 75


async def test_fan_set_preset_mode(rest):
    """fan.set_preset_mode sets preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.pm_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_preset_mode", {
        "entity_id": eid,
        "preset_mode": "auto",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "auto"


# ── Media Player Variants ──────────────────────────────

async def test_media_player_volume_set(rest):
    """media_player.volume_set sets volume_level attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.vol_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid,
        "volume_level": 0.5,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.5


async def test_media_player_volume_mute(rest):
    """media_player.volume_mute sets is_volume_muted attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mute_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": eid,
        "is_volume_muted": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["is_volume_muted"] is True


async def test_media_player_play_pause_cycle(rest):
    """media_player: play → pause cycle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.pp_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"
    await rest.call_service("media_player", "media_pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"
