"""
CTS -- Timer & Counter Entity Tests

Tests timer domain services: start, pause, cancel, finish.
Tests counter domain services: increment, decrement, reset.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Timer ─────────────────────────────────────────────────

async def test_timer_start(rest):
    """timer.start sets state to 'active'."""
    entity_id = "timer.test_start"
    await rest.set_state(entity_id, "idle")
    await rest.call_service("timer", "start", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "active"


async def test_timer_pause(rest):
    """timer.pause sets state to 'paused'."""
    entity_id = "timer.test_pause"
    await rest.set_state(entity_id, "active")
    await rest.call_service("timer", "pause", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "paused"


async def test_timer_cancel(rest):
    """timer.cancel sets state to 'idle'."""
    entity_id = "timer.test_cancel"
    await rest.set_state(entity_id, "active")
    await rest.call_service("timer", "cancel", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "idle"


async def test_timer_finish(rest):
    """timer.finish sets state to 'idle'."""
    entity_id = "timer.test_finish"
    await rest.set_state(entity_id, "active")
    await rest.call_service("timer", "finish", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "idle"


async def test_timer_lifecycle(rest):
    """Timer goes through lifecycle: idle -> active -> paused -> active -> idle."""
    entity_id = "timer.lifecycle"
    await rest.set_state(entity_id, "idle")

    await rest.call_service("timer", "start", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "active"

    await rest.call_service("timer", "pause", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "paused"

    await rest.call_service("timer", "start", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "active"

    await rest.call_service("timer", "cancel", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "idle"


# ── Counter ───────────────────────────────────────────────

async def test_counter_increment(rest):
    """counter.increment increases counter by 1."""
    entity_id = "counter.test_inc"
    await rest.set_state(entity_id, "0")
    await rest.call_service("counter", "increment", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "1"


async def test_counter_decrement(rest):
    """counter.decrement decreases counter by 1."""
    entity_id = "counter.test_dec"
    await rest.set_state(entity_id, "5")
    await rest.call_service("counter", "decrement", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "4"


async def test_counter_reset(rest):
    """counter.reset returns counter to initial (default 0)."""
    entity_id = "counter.test_reset"
    await rest.set_state(entity_id, "42")
    await rest.call_service("counter", "reset", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "0"


async def test_counter_reset_with_initial(rest):
    """counter.reset returns counter to initial attribute value."""
    entity_id = "counter.test_reset_initial"
    await rest.set_state(entity_id, "99", {"initial": 10})
    await rest.call_service("counter", "reset", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "10"


async def test_counter_multiple_increments(rest):
    """Multiple increments accumulate correctly."""
    entity_id = "counter.multi_inc"
    await rest.set_state(entity_id, "0")
    for _ in range(5):
        await rest.call_service("counter", "increment", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "5"


async def test_counter_negative(rest):
    """Counter can go negative with decrement."""
    entity_id = "counter.negative"
    await rest.set_state(entity_id, "0")
    await rest.call_service("counter", "decrement", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "-1"
