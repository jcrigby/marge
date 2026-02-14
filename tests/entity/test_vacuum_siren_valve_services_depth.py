"""
CTS -- Vacuum, Siren, and Valve Service Depth Tests

Tests service handlers for vacuum (start, stop, pause, return_to_base),
siren (turn_on, turn_off, toggle), and valve (open_valve, close_valve, toggle).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Vacuum Services ──────────────────────────────────────

async def test_vacuum_start(rest):
    """vacuum.start sets state to cleaning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vsvd_start_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("vacuum", "start", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "cleaning"


async def test_vacuum_stop(rest):
    """vacuum.stop sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vsvd_stop_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "stop", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_vacuum_pause(rest):
    """vacuum.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vsvd_pause_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base sets state to returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vsvd_rtb_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "returning"


async def test_vacuum_lifecycle(rest):
    """Vacuum full lifecycle: idle → cleaning → paused → cleaning → returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vsvd_lc_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "returning"


# ── Siren Services ───────────────────────────────────────

async def test_siren_turn_on(rest):
    """siren.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.vsvd_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_siren_turn_off(rest):
    """siren.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.vsvd_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("siren", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_siren_toggle_on_to_off(rest):
    """siren.toggle from on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.vsvd_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_siren_toggle_off_to_on(rest):
    """siren.toggle from off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.vsvd_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Valve Services ───────────────────────────────────────

async def test_valve_open(rest):
    """valve.open_valve sets state to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vsvd_open_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "open_valve", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"


async def test_valve_close(rest):
    """valve.close_valve sets state to closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vsvd_close_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("valve", "close_valve", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_valve_toggle_open_to_closed(rest):
    """valve.toggle from open → closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vsvd_tog1_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_valve_toggle_closed_to_open(rest):
    """valve.toggle from closed → open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vsvd_tog2_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"
