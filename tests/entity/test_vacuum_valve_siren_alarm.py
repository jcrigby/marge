"""
CTS -- Alarm Control Panel Lifecycle Test

Tests alarm_control_panel full lifecycle through multiple state transitions.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_alarm_lifecycle(rest):
    """Alarm full lifecycle: disarmed -> armed_home -> triggered -> disarmed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alc_{tag}"
    await rest.set_state(eid, "disarmed")

    for service, expected in [
        ("arm_home", "armed_home"),
        ("trigger", "triggered"),
        ("disarm", "disarmed"),
        ("arm_away", "armed_away"),
        ("disarm", "disarmed"),
    ]:
        await rest.client.post(
            f"{rest.base_url}/api/services/alarm_control_panel/{service}",
            json={"entity_id": eid},
            headers=rest._headers(),
        )
        state = await rest.get_state(eid)
        assert state["state"] == expected, f"After {service}: expected {expected}"
