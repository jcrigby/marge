"""
CTS -- Alarm Control Panel & Lock Services Depth Tests

Tests alarm_control_panel domain services (arm_home, arm_away,
arm_night, disarm, trigger) and lock domain services (lock,
unlock, open) with state transitions and attribute preservation.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Alarm Arm Home ──────────────────────────────────────

async def test_alarm_arm_home(rest):
    """alarm_control_panel.arm_home → armed_home."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alsd_home_{tag}"
    await rest.set_state(eid, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "armed_home"


async def test_alarm_arm_away(rest):
    """alarm_control_panel.arm_away → armed_away."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alsd_away_{tag}"
    await rest.set_state(eid, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_away", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "armed_away"


async def test_alarm_arm_night(rest):
    """alarm_control_panel.arm_night → armed_night."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alsd_night_{tag}"
    await rest.set_state(eid, "disarmed")
    await rest.call_service("alarm_control_panel", "arm_night", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "armed_night"


async def test_alarm_disarm(rest):
    """alarm_control_panel.disarm → disarmed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alsd_disarm_{tag}"
    await rest.set_state(eid, "armed_home")
    await rest.call_service("alarm_control_panel", "disarm", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "disarmed"


async def test_alarm_trigger(rest):
    """alarm_control_panel.trigger → triggered."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alsd_trig_{tag}"
    await rest.set_state(eid, "armed_away")
    await rest.call_service("alarm_control_panel", "trigger", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "triggered"


async def test_alarm_preserves_attrs(rest):
    """Alarm services preserve existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alsd_attr_{tag}"
    await rest.set_state(eid, "disarmed", {"code_format": "number"})
    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "armed_home"
    assert state["attributes"]["code_format"] == "number"


# ── Alarm Full Lifecycle ────────────────────────────────

async def test_alarm_full_lifecycle(rest):
    """Alarm: disarmed → arm_home → disarm → arm_away → trigger → disarm."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.alsd_lc_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "armed_home"

    await rest.call_service("alarm_control_panel", "disarm", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "disarmed"

    await rest.call_service("alarm_control_panel", "arm_away", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "armed_away"

    await rest.call_service("alarm_control_panel", "trigger", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "triggered"

    await rest.call_service("alarm_control_panel", "disarm", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "disarmed"


# ── Lock ────────────────────────────────────────────────

async def test_lock_lock(rest):
    """lock.lock → locked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.alsd_lock_{tag}"
    await rest.set_state(eid, "unlocked")
    await rest.call_service("lock", "lock", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "locked"


async def test_lock_unlock(rest):
    """lock.unlock → unlocked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.alsd_unlock_{tag}"
    await rest.set_state(eid, "locked")
    await rest.call_service("lock", "unlock", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "unlocked"


async def test_lock_open(rest):
    """lock.open → open (latch release)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.alsd_open_{tag}"
    await rest.set_state(eid, "locked")
    await rest.call_service("lock", "open", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"


async def test_lock_preserves_attrs(rest):
    """Lock services preserve existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.alsd_lattr_{tag}"
    await rest.set_state(eid, "unlocked", {"battery": 85})
    await rest.call_service("lock", "lock", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "locked"
    assert state["attributes"]["battery"] == 85


async def test_lock_full_lifecycle(rest):
    """Lock: unlocked → lock → unlock → open → lock."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.alsd_llc_{tag}"
    await rest.set_state(eid, "unlocked")

    await rest.call_service("lock", "lock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "locked"

    await rest.call_service("lock", "unlock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "unlocked"

    await rest.call_service("lock", "open", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"

    await rest.call_service("lock", "lock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "locked"
