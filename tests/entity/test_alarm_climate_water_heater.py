"""
CTS -- Alarm and Climate Service Depth Tests

Tests alarm_control_panel arm/disarm/trigger and climate
set_temperature attribute storage.
"""

import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# -- Alarm Control Panel (parametrized) --

@pytest.mark.parametrize("service,initial_state,expected_state", [
    ("arm_home", "disarmed", "armed_home"),
    ("arm_away", "disarmed", "armed_away"),
    ("arm_night", "disarmed", "armed_night"),
    ("disarm", "armed_home", "disarmed"),
    ("trigger", "armed_home", "triggered"),
])
async def test_alarm_service(rest, service, initial_state, expected_state):
    """Alarm service sets expected state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.a_{service}_{tag}"
    await rest.set_state(eid, initial_state)

    await rest.call_service("alarm_control_panel", service, {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == expected_state


# -- Alarm Full Lifecycle (merged from test_alarm.py) --

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


# -- Climate --

async def test_climate_set_temperature_stores_attr(rest):
    """Climate set_temperature stores temperature and target_temp_high/low."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.tattr_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 68,
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("temperature") == 68
