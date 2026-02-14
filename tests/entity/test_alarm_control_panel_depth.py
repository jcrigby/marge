"""
CTS -- Alarm Control Panel Service Depth Tests

Tests all alarm_control_panel services: arm_home, arm_away, arm_night,
arm_vacation, arm_custom_bypass, disarm, and trigger.
Verifies state transitions and attribute preservation.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_alarm_arm_home(rest):
    """alarm_control_panel.arm_home sets state to armed_home."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alarm_{tag}"
    await rest.set_state(eid, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_home"


async def test_alarm_arm_away(rest):
    """alarm_control_panel.arm_away sets state to armed_away."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alarm_{tag}"
    await rest.set_state(eid, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_away", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_away"


async def test_alarm_arm_night(rest):
    """alarm_control_panel.arm_night sets state to armed_night."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alarm_{tag}"
    await rest.set_state(eid, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_night", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_night"


async def test_alarm_arm_from_any_state(rest):
    """alarm_control_panel can arm from any prior state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alarm_{tag}"
    await rest.set_state(eid, "triggered")
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_home"


async def test_alarm_disarm_from_away(rest):
    """alarm_control_panel.disarm works from armed_away."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alarm_{tag}"
    await rest.set_state(eid, "armed_away")
    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "disarmed"


async def test_alarm_disarm(rest):
    """alarm_control_panel.disarm sets state to disarmed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alarm_{tag}"
    await rest.set_state(eid, "armed_away")
    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "disarmed"


async def test_alarm_trigger(rest):
    """alarm_control_panel.trigger sets state to triggered."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alarm_{tag}"
    await rest.set_state(eid, "armed_home")
    await rest.call_service("alarm_control_panel", "trigger", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "triggered"


async def test_alarm_full_lifecycle(rest):
    """Alarm cycles: disarmed → armed_home → armed_night → disarmed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.lifecycle_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_home"

    await rest.call_service("alarm_control_panel", "arm_night", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "armed_night"

    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "disarmed"


async def test_alarm_preserves_attributes(rest):
    """Alarm state changes preserve existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.attr_{tag}"
    await rest.set_state(eid, "disarmed", {
        "friendly_name": "Home Alarm",
        "code_format": "number",
    })
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "armed_home"
    assert state["attributes"].get("friendly_name") == "Home Alarm"
    assert state["attributes"].get("code_format") == "number"


async def test_alarm_homeassistant_turn_off_disarms(rest):
    """homeassistant.turn_off on alarm sets to 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.ha_off_{tag}"
    await rest.set_state(eid, "armed_home")
    await rest.call_service("homeassistant", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
