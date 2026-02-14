"""
CTS -- Domain State Format Validation Tests

Verifies that service calls for each domain produce the expected
state values (on/off, locked/unlocked, open/closed, etc.).
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_light_on_off_states(rest):
    """Light domain: turn_on → 'on', turn_off → 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.fmt_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("light", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_switch_on_off_states(rest):
    """Switch domain: turn_on → 'on', turn_off → 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.fmt_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_lock_locked_unlocked_states(rest):
    """Lock domain: lock → 'locked', unlock → 'unlocked'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.fmt_{tag}"
    await rest.set_state(eid, "unlocked")
    await rest.call_service("lock", "lock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "locked"
    await rest.call_service("lock", "unlock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "unlocked"


async def test_cover_open_closed_states(rest):
    """Cover domain: open → 'open', close → 'closed'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.fmt_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"
    await rest.call_service("cover", "close_cover", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_siren_on_off_states(rest):
    """Siren domain: turn_on → 'on', turn_off → 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.fmt_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("siren", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_vacuum_state_values(rest):
    """Vacuum domain: start → 'cleaning', stop → 'idle', return_to_base → 'returning'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.fmt_{tag}"
    await rest.set_state(eid, "docked")

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("vacuum", "stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"

    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "returning"


async def test_valve_open_closed_states(rest):
    """Valve domain: open → 'open', close → 'closed'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.fmt_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "open_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"
    await rest.call_service("valve", "close_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_alarm_arm_states(rest):
    """Alarm panel: arm_home → 'armed_home', arm_away → 'armed_away', disarm → 'disarmed'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.fmt_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_home"

    await rest.call_service("alarm_control_panel", "arm_away", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_away"

    await rest.call_service("alarm_control_panel", "arm_night", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_night"

    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "disarmed"


async def test_fan_on_off_states(rest):
    """Fan domain: turn_on → 'on', turn_off → 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fmt_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("fan", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_camera_streaming_idle(rest):
    """Camera domain: turn_on → 'streaming', turn_off → 'idle'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.fmt_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("camera", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "streaming"
    await rest.call_service("camera", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


async def test_number_set_value_state(rest):
    """Number domain: set_value stores numeric string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.fmt_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("number", "set_value", {
        "entity_id": eid,
        "value": 75,
    })
    assert "75" in (await rest.get_state(eid))["state"]


async def test_select_option_state(rest):
    """Select domain: select_option stores option string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.fmt_{tag}"
    await rest.set_state(eid, "option_a")
    await rest.call_service("select", "select_option", {
        "entity_id": eid,
        "option": "option_b",
    })
    assert (await rest.get_state(eid))["state"] == "option_b"
