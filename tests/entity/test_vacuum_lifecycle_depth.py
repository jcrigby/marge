"""
CTS -- Vacuum Lifecycle Depth Tests

Tests vacuum domain services: start, stop, pause, return_to_base,
attribute preservation, and full lifecycle scenarios.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Start ───────────────────────────────────────────────

async def test_vacuum_start(rest):
    """vacuum.start → cleaning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vld_start_{tag}"
    await rest.set_state(eid, "docked")
    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"


# ── Stop ────────────────────────────────────────────────

async def test_vacuum_stop(rest):
    """vacuum.stop → idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vld_stop_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


# ── Pause ───────────────────────────────────────────────

async def test_vacuum_pause(rest):
    """vacuum.pause → paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vld_pause_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"


# ── Return to Base ──────────────────────────────────────

async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base → returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vld_rtb_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "returning"


# ── Attribute Preservation ──────────────────────────────

async def test_vacuum_start_preserves_attrs(rest):
    """vacuum.start preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vld_attr_{tag}"
    await rest.set_state(eid, "docked", {"battery_level": 100})
    await rest.call_service("vacuum", "start", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "cleaning"
    assert state["attributes"]["battery_level"] == 100


# ── Full Lifecycle ──────────────────────────────────────

async def test_vacuum_full_lifecycle(rest):
    """Vacuum: docked → start → pause → start → return → stop."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vld_lc_{tag}"
    await rest.set_state(eid, "docked")

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "returning"

    await rest.call_service("vacuum", "stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"
