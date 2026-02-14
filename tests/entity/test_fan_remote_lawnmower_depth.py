"""
CTS -- Fan, Remote, Lawn Mower Services Depth Tests

Tests fan domain services (turn_on with percentage/preset,
turn_off, toggle, set_direction, set_preset_mode, set_percentage),
remote domain services (turn_on, turn_off, send_command), and
lawn_mower domain services (start_mowing, pause, dock).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Fan Turn On ─────────────────────────────────────────

async def test_fan_turn_on(rest):
    """fan.turn_on → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_fan_turn_on_with_percentage(rest):
    """fan.turn_on with percentage sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_onpct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "turn_on", {
        "entity_id": eid, "percentage": 75,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75


async def test_fan_turn_on_with_preset(rest):
    """fan.turn_on with preset_mode sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_onpre_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "turn_on", {
        "entity_id": eid, "preset_mode": "sleep",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["preset_mode"] == "sleep"


# ── Fan Turn Off / Toggle ──────────────────────────────

async def test_fan_turn_off(rest):
    """fan.turn_off → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_fan_toggle_on_to_off(rest):
    """fan.toggle from on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_fan_toggle_off_to_on(rest):
    """fan.toggle from off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


# ── Fan Set Direction / Preset / Percentage ────────────

async def test_fan_set_direction(rest):
    """fan.set_direction sets direction attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_dir_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_direction", {
        "entity_id": eid, "direction": "reverse",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["direction"] == "reverse"


async def test_fan_set_preset_mode(rest):
    """fan.set_preset_mode sets preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_pre_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_preset_mode", {
        "entity_id": eid, "preset_mode": "natural",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "natural"


async def test_fan_set_percentage(rest):
    """fan.set_percentage sets percentage and infers state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_pct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid, "percentage": 50,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 50


async def test_fan_set_percentage_zero_off(rest):
    """fan.set_percentage at 0 → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.frld_pct0_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid, "percentage": 0,
    })
    assert (await rest.get_state(eid))["state"] == "off"


# ── Remote ──────────────────────────────────────────────

async def test_remote_turn_on(rest):
    """remote.turn_on → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"remote.frld_ron_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("remote", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_remote_turn_off(rest):
    """remote.turn_off → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"remote.frld_roff_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("remote", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_remote_send_command(rest):
    """remote.send_command stores last_command attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"remote.frld_rcmd_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("remote", "send_command", {
        "entity_id": eid, "command": "volume_up",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["last_command"] == "volume_up"


# ── Lawn Mower ──────────────────────────────────────────

async def test_lawn_mower_start_mowing(rest):
    """lawn_mower.start_mowing → mowing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.frld_mow_{tag}"
    await rest.set_state(eid, "docked")
    await rest.call_service("lawn_mower", "start_mowing", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "mowing"


async def test_lawn_mower_pause(rest):
    """lawn_mower.pause → paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.frld_pause_{tag}"
    await rest.set_state(eid, "mowing")
    await rest.call_service("lawn_mower", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"


async def test_lawn_mower_dock(rest):
    """lawn_mower.dock → docked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.frld_dock_{tag}"
    await rest.set_state(eid, "mowing")
    await rest.call_service("lawn_mower", "dock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "docked"


async def test_lawn_mower_full_lifecycle(rest):
    """Lawn mower: docked → mow → pause → mow → dock."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.frld_lc_{tag}"
    await rest.set_state(eid, "docked")

    await rest.call_service("lawn_mower", "start_mowing", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "mowing"

    await rest.call_service("lawn_mower", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("lawn_mower", "start_mowing", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "mowing"

    await rest.call_service("lawn_mower", "dock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "docked"
