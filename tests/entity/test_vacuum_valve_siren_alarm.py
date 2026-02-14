"""
CTS -- Vacuum, Valve, Siren, Alarm Control Panel Domain Service Tests

Tests service handlers for: vacuum (start/stop/pause/return_to_base),
valve (open/close/toggle), siren (on/off/toggle), and
alarm_control_panel (arm_home/arm_away/arm_night/disarm/trigger).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Vacuum ─────────────────────────────────────────────

async def test_vacuum_start(rest):
    """vacuum.start sets state to cleaning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.v_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/vacuum/start",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "cleaning"


async def test_vacuum_stop(rest):
    """vacuum.stop sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vs_{tag}"
    await rest.set_state(eid, "cleaning")

    await rest.client.post(
        f"{rest.base_url}/api/services/vacuum/stop",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_vacuum_pause(rest):
    """vacuum.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vp_{tag}"
    await rest.set_state(eid, "cleaning")

    await rest.client.post(
        f"{rest.base_url}/api/services/vacuum/pause",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base sets state to returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vr_{tag}"
    await rest.set_state(eid, "cleaning")

    await rest.client.post(
        f"{rest.base_url}/api/services/vacuum/return_to_base",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "returning"


async def test_vacuum_lifecycle(rest):
    """Vacuum full lifecycle: idle → cleaning → paused → cleaning → returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vlc_{tag}"
    await rest.set_state(eid, "idle")

    for service, expected in [
        ("start", "cleaning"),
        ("pause", "paused"),
        ("start", "cleaning"),
        ("return_to_base", "returning"),
    ]:
        await rest.client.post(
            f"{rest.base_url}/api/services/vacuum/{service}",
            json={"entity_id": eid},
            headers=rest._headers(),
        )
        state = await rest.get_state(eid)
        assert state["state"] == expected, f"After {service}: expected {expected}"


# ── Valve ──────────────────────────────────────────────

async def test_valve_open(rest):
    """valve.open_valve sets state to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.v_{tag}"
    await rest.set_state(eid, "closed")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/valve/open_valve",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "open"


async def test_valve_close(rest):
    """valve.close_valve sets state to closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vc_{tag}"
    await rest.set_state(eid, "open")

    await rest.client.post(
        f"{rest.base_url}/api/services/valve/close_valve",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_valve_toggle_open_to_closed(rest):
    """valve.toggle from open to closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vt_{tag}"
    await rest.set_state(eid, "open")

    await rest.client.post(
        f"{rest.base_url}/api/services/valve/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_valve_toggle_closed_to_open(rest):
    """valve.toggle from closed to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vt2_{tag}"
    await rest.set_state(eid, "closed")

    await rest.client.post(
        f"{rest.base_url}/api/services/valve/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "open"


# ── Siren ──────────────────────────────────────────────

async def test_siren_turn_on(rest):
    """siren.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.s_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/siren/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_siren_turn_off(rest):
    """siren.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.so_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/siren/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_siren_toggle(rest):
    """siren.toggle flips on→off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.st_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/siren/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Alarm Control Panel ───────────────────────────────

async def test_alarm_arm_home(rest):
    """alarm_control_panel.arm_home sets armed_home."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.a_{tag}"
    await rest.set_state(eid, "disarmed")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/alarm_control_panel/arm_home",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "armed_home"


async def test_alarm_arm_away(rest):
    """alarm_control_panel.arm_away sets armed_away."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.aa_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.client.post(
        f"{rest.base_url}/api/services/alarm_control_panel/arm_away",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "armed_away"


async def test_alarm_arm_night(rest):
    """alarm_control_panel.arm_night sets armed_night."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.an_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.client.post(
        f"{rest.base_url}/api/services/alarm_control_panel/arm_night",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "armed_night"


async def test_alarm_disarm(rest):
    """alarm_control_panel.disarm sets disarmed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.ad_{tag}"
    await rest.set_state(eid, "armed_home")

    await rest.client.post(
        f"{rest.base_url}/api/services/alarm_control_panel/disarm",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "disarmed"


async def test_alarm_trigger(rest):
    """alarm_control_panel.trigger sets triggered."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.at_{tag}"
    await rest.set_state(eid, "armed_home")

    await rest.client.post(
        f"{rest.base_url}/api/services/alarm_control_panel/trigger",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "triggered"


async def test_alarm_lifecycle(rest):
    """Alarm full lifecycle: disarmed → armed_home → triggered → disarmed."""
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
