"""
CTS -- Alarm Control Panel Service Depth Tests

Tests alarm_control_panel domain services: arm_home, arm_away,
arm_night, disarm, trigger, and state transition sequences.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_alarm_arm_home(rest):
    """arm_home sets state to armed_home."""
    await rest.set_state("alarm_control_panel.depth_ah", "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": "alarm_control_panel.depth_ah",
    })
    state = await rest.get_state("alarm_control_panel.depth_ah")
    assert state["state"] == "armed_home"


async def test_alarm_arm_away(rest):
    """arm_away sets state to armed_away."""
    await rest.set_state("alarm_control_panel.depth_aa", "disarmed")
    await rest.call_service("alarm_control_panel", "arm_away", {
        "entity_id": "alarm_control_panel.depth_aa",
    })
    state = await rest.get_state("alarm_control_panel.depth_aa")
    assert state["state"] == "armed_away"


async def test_alarm_arm_night(rest):
    """arm_night sets state to armed_night."""
    await rest.set_state("alarm_control_panel.depth_an", "disarmed")
    await rest.call_service("alarm_control_panel", "arm_night", {
        "entity_id": "alarm_control_panel.depth_an",
    })
    state = await rest.get_state("alarm_control_panel.depth_an")
    assert state["state"] == "armed_night"


async def test_alarm_disarm(rest):
    """disarm sets state to disarmed."""
    await rest.set_state("alarm_control_panel.depth_dis", "armed_home")
    await rest.call_service("alarm_control_panel", "disarm", {
        "entity_id": "alarm_control_panel.depth_dis",
    })
    state = await rest.get_state("alarm_control_panel.depth_dis")
    assert state["state"] == "disarmed"


async def test_alarm_trigger(rest):
    """trigger sets state to triggered."""
    await rest.set_state("alarm_control_panel.depth_trig", "armed_away")
    await rest.call_service("alarm_control_panel", "trigger", {
        "entity_id": "alarm_control_panel.depth_trig",
    })
    state = await rest.get_state("alarm_control_panel.depth_trig")
    assert state["state"] == "triggered"


async def test_alarm_sequence_arm_trigger_disarm(rest):
    """Full alarm sequence: disarmed -> armed -> triggered -> disarmed."""
    eid = "alarm_control_panel.depth_seq"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_away", {"entity_id": eid})
    s1 = await rest.get_state(eid)
    assert s1["state"] == "armed_away"

    await rest.call_service("alarm_control_panel", "trigger", {"entity_id": eid})
    s2 = await rest.get_state(eid)
    assert s2["state"] == "triggered"

    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": eid})
    s3 = await rest.get_state(eid)
    assert s3["state"] == "disarmed"


async def test_alarm_arm_preserves_attrs(rest):
    """Alarm arm preserves existing attributes."""
    await rest.set_state("alarm_control_panel.depth_attr", "disarmed", {"code_required": True})
    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": "alarm_control_panel.depth_attr",
    })
    state = await rest.get_state("alarm_control_panel.depth_attr")
    assert state["state"] == "armed_home"
    assert state["attributes"]["code_required"] is True
