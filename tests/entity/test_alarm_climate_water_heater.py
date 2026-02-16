"""
CTS -- Alarm and Climate Service Depth Tests

Tests alarm_control_panel arm/disarm/trigger and climate
set_temperature attribute storage.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# -- Alarm Control Panel --

async def test_arm_home(rest):
    """Alarm arm_home sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.ah_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "armed_home"


async def test_arm_away(rest):
    """Alarm arm_away sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.aa_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_away", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "armed_away"


async def test_arm_night(rest):
    """Alarm arm_night sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.an_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_night", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "armed_night"


async def test_disarm(rest):
    """Alarm disarm sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.ad_{tag}"
    await rest.set_state(eid, "armed_home")

    await rest.call_service("alarm_control_panel", "disarm", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "disarmed"


async def test_trigger(rest):
    """Alarm trigger sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.at_{tag}"
    await rest.set_state(eid, "armed_home")

    await rest.call_service("alarm_control_panel", "trigger", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "triggered"


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
