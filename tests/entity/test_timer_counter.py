"""
CTS -- Timer & Counter Entity Tests

Tests timer domain services: start, pause, cancel, finish.
Tests counter domain services: increment, decrement, reset.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Timer state transitions (parametrized) ───────────────────

@pytest.mark.parametrize("initial_state,service,expected_state", [
    ("idle", "start", "active"),
    ("active", "pause", "paused"),
    ("active", "cancel", "idle"),
    ("active", "finish", "idle"),
])
async def test_timer_service(rest, initial_state, service, expected_state):
    """Timer service sets expected state."""
    entity_id = f"timer.test_{service}"
    await rest.set_state(entity_id, initial_state)
    await rest.call_service("timer", service, {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == expected_state


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


# ── Counter ──────────────────────────────────────────────────

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


@pytest.mark.parametrize("initial_value,initial_attr,expected", [
    ("42", {}, "0"),
    ("99", {"initial": 10}, "10"),
    ("10", {"initial": 5}, "5"),
    ("5", {"initial": 0}, "0"),
])
async def test_counter_reset(rest, initial_value, initial_attr, expected):
    """counter.reset returns counter to initial value (default 0)."""
    entity_id = f"counter.test_reset_{initial_value}_{expected}"
    await rest.set_state(entity_id, initial_value, initial_attr if initial_attr else None)
    await rest.call_service("counter", "reset", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == expected


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


# ── Merged from depth: counter preserves attributes ──────────

async def test_counter_preserves_attrs(rest):
    """Counter operations preserve attributes."""
    await rest.set_state("counter.depth_c7", "0", {"step": 1, "minimum": 0})
    await rest.call_service("counter", "increment", {"entity_id": "counter.depth_c7"})
    state = await rest.get_state("counter.depth_c7")
    assert state["state"] == "1"
    assert state["attributes"]["step"] == 1
