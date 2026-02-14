"""
CTS -- Counter Services Depth Tests

Tests counter domain services: increment, decrement, reset,
boundary behavior, and attribute preservation.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Increment ───────────────────────────────────────────

async def test_counter_increment_from_zero(rest):
    """counter.increment from 0 → 1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.csd_inc0_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("counter", "increment", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "1"


async def test_counter_increment_multiple(rest):
    """counter.increment multiple times."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.csd_incm_{tag}"
    await rest.set_state(eid, "5")
    await rest.call_service("counter", "increment", {"entity_id": eid})
    await rest.call_service("counter", "increment", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "7"


# ── Decrement ───────────────────────────────────────────

async def test_counter_decrement(rest):
    """counter.decrement from 5 → 4."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.csd_dec_{tag}"
    await rest.set_state(eid, "5")
    await rest.call_service("counter", "decrement", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "4"


async def test_counter_decrement_below_zero(rest):
    """counter.decrement below zero goes negative."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.csd_neg_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("counter", "decrement", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "-1"


# ── Reset ───────────────────────────────────────────────

async def test_counter_reset(rest):
    """counter.reset sets state to 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.csd_rst_{tag}"
    await rest.set_state(eid, "42")
    await rest.call_service("counter", "reset", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "0"


# ── Attribute Preservation ──────────────────────────────

async def test_counter_increment_preserves_attrs(rest):
    """counter.increment preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.csd_iattr_{tag}"
    await rest.set_state(eid, "10", {"step": 1, "minimum": 0})
    await rest.call_service("counter", "increment", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["step"] == 1


# ── Full Lifecycle ──────────────────────────────────────

async def test_counter_full_lifecycle(rest):
    """Counter: 0 → inc → inc → dec → reset."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.csd_lc_{tag}"
    await rest.set_state(eid, "0")

    await rest.call_service("counter", "increment", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "1"

    await rest.call_service("counter", "increment", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "2"

    await rest.call_service("counter", "decrement", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "1"

    await rest.call_service("counter", "reset", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "0"
