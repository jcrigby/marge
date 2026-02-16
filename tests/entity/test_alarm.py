"""
CTS -- Alarm Control Panel Entity Tests

Tests alarm_control_panel lifecycle.
"""

import pytest

pytestmark = pytest.mark.asyncio


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
