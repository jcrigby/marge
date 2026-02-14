"""
CTS -- Alarm Control Panel Entity Tests

Tests alarm_control_panel domain services: arm_home, arm_away, arm_night, disarm, trigger.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_alarm_arm_home(rest):
    """alarm_control_panel.arm_home sets state to 'armed_home'."""
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_home"


async def test_alarm_arm_away(rest):
    """alarm_control_panel.arm_away sets state to 'armed_away'."""
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_away", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_away"


async def test_alarm_arm_night(rest):
    """alarm_control_panel.arm_night sets state to 'armed_night'."""
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_night", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_night"


async def test_alarm_disarm(rest):
    """alarm_control_panel.disarm sets state to 'disarmed'."""
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "armed_away")
    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "disarmed"


async def test_alarm_trigger(rest):
    """alarm_control_panel.trigger sets state to 'triggered'."""
    entity_id = "alarm_control_panel.test_trigger"
    await rest.set_state(entity_id, "armed_home")
    await rest.call_service("alarm_control_panel", "trigger", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "triggered"


async def test_alarm_full_lifecycle(rest):
    """Alarm goes through full lifecycle: disarmed -> armed_home -> armed_away -> triggered -> disarmed."""
    entity_id = "alarm_control_panel.lifecycle"
    await rest.set_state(entity_id, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_home"

    await rest.call_service("alarm_control_panel", "arm_away", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_away"

    await rest.call_service("alarm_control_panel", "trigger", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "triggered"

    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "disarmed"
