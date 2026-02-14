"""
CTS -- Timer and Counter Service Depth Tests

Tests timer (start, pause, cancel, finish) and counter (increment,
decrement, reset) domain handlers with state transitions.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Timer ────────────────────────────────────────────────

async def test_timer_start(rest):
    """timer start sets state to active."""
    await rest.set_state("timer.depth_t1", "idle")
    await rest.call_service("timer", "start", {"entity_id": "timer.depth_t1"})
    state = await rest.get_state("timer.depth_t1")
    assert state["state"] == "active"


async def test_timer_pause(rest):
    """timer pause sets state to paused."""
    await rest.set_state("timer.depth_t2", "active")
    await rest.call_service("timer", "pause", {"entity_id": "timer.depth_t2"})
    state = await rest.get_state("timer.depth_t2")
    assert state["state"] == "paused"


async def test_timer_cancel(rest):
    """timer cancel sets state to idle."""
    await rest.set_state("timer.depth_t3", "active")
    await rest.call_service("timer", "cancel", {"entity_id": "timer.depth_t3"})
    state = await rest.get_state("timer.depth_t3")
    assert state["state"] == "idle"


async def test_timer_finish(rest):
    """timer finish sets state to idle."""
    await rest.set_state("timer.depth_t4", "active")
    await rest.call_service("timer", "finish", {"entity_id": "timer.depth_t4"})
    state = await rest.get_state("timer.depth_t4")
    assert state["state"] == "idle"


async def test_timer_cycle(rest):
    """Full timer cycle: idle -> active -> paused -> active -> idle."""
    eid = "timer.depth_cycle"
    await rest.set_state(eid, "idle")

    await rest.call_service("timer", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "active"

    await rest.call_service("timer", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("timer", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "active"

    await rest.call_service("timer", "cancel", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


# ── Counter ──────────────────────────────────────────────

async def test_counter_increment(rest):
    """counter increment increases state by 1."""
    await rest.set_state("counter.depth_c1", "5")
    await rest.call_service("counter", "increment", {"entity_id": "counter.depth_c1"})
    state = await rest.get_state("counter.depth_c1")
    assert state["state"] == "6"


async def test_counter_decrement(rest):
    """counter decrement decreases state by 1."""
    await rest.set_state("counter.depth_c2", "5")
    await rest.call_service("counter", "decrement", {"entity_id": "counter.depth_c2"})
    state = await rest.get_state("counter.depth_c2")
    assert state["state"] == "4"


async def test_counter_reset(rest):
    """counter reset returns to initial value."""
    await rest.set_state("counter.depth_c3", "10", {"initial": 0})
    await rest.call_service("counter", "reset", {"entity_id": "counter.depth_c3"})
    state = await rest.get_state("counter.depth_c3")
    assert state["state"] == "0"


async def test_counter_reset_nonzero_initial(rest):
    """counter reset to nonzero initial value."""
    await rest.set_state("counter.depth_c4", "10", {"initial": 5})
    await rest.call_service("counter", "reset", {"entity_id": "counter.depth_c4"})
    state = await rest.get_state("counter.depth_c4")
    assert state["state"] == "5"


async def test_counter_multiple_increments(rest):
    """Multiple increments accumulate correctly."""
    await rest.set_state("counter.depth_c5", "0")
    for _ in range(5):
        await rest.call_service("counter", "increment", {"entity_id": "counter.depth_c5"})
    state = await rest.get_state("counter.depth_c5")
    assert state["state"] == "5"


async def test_counter_decrement_below_zero(rest):
    """Counter can go below zero."""
    await rest.set_state("counter.depth_c6", "0")
    await rest.call_service("counter", "decrement", {"entity_id": "counter.depth_c6"})
    state = await rest.get_state("counter.depth_c6")
    assert state["state"] == "-1"


async def test_counter_preserves_attrs(rest):
    """Counter operations preserve attributes."""
    await rest.set_state("counter.depth_c7", "0", {"step": 1, "minimum": 0})
    await rest.call_service("counter", "increment", {"entity_id": "counter.depth_c7"})
    state = await rest.get_state("counter.depth_c7")
    assert state["state"] == "1"
    assert state["attributes"]["step"] == 1
