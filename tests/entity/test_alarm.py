"""CTS — Alarm Control Panel Entity Tests."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_alarm_arm_home(rest):
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_home"


async def test_alarm_arm_away(rest):
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_away", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_away"


async def test_alarm_arm_night(rest):
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_night", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "armed_night"


async def test_alarm_disarm(rest):
    entity_id = "alarm_control_panel.test_alarm"
    await rest.set_state(entity_id, "armed_away")
    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "disarmed"
