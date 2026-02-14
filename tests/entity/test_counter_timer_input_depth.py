"""
CTS -- Counter, Timer, and Input Helper Depth Tests

Tests counter increment/decrement/reset, timer start/pause/cancel/finish,
input_number set_value, input_text set_value, input_select select_option,
and input_boolean toggle lifecycle.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Counter ─────────────────────────────────────────────────

async def test_counter_increment(rest):
    """counter.increment adds 1 to current value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ct_{tag}"
    await rest.set_state(eid, "0")

    await rest.call_service("counter", "increment", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "1"


async def test_counter_decrement(rest):
    """counter.decrement subtracts 1 from current value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ct_dec_{tag}"
    await rest.set_state(eid, "5")

    await rest.call_service("counter", "decrement", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "4"


async def test_counter_multiple_increments(rest):
    """Multiple increments accumulate correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ct_multi_{tag}"
    await rest.set_state(eid, "0")

    for _ in range(5):
        await rest.call_service("counter", "increment", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "5"


async def test_counter_decrement_below_zero(rest):
    """counter.decrement goes negative."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ct_neg_{tag}"
    await rest.set_state(eid, "0")

    await rest.call_service("counter", "decrement", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "-1"


async def test_counter_reset(rest):
    """counter.reset returns to initial value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ct_rst_{tag}"
    await rest.set_state(eid, "10", {"initial": 0})

    await rest.call_service("counter", "reset", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "0"


async def test_counter_reset_with_custom_initial(rest):
    """counter.reset uses initial attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ct_rsti_{tag}"
    await rest.set_state(eid, "99", {"initial": 42})

    await rest.call_service("counter", "reset", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "42"


# ── Timer ───────────────────────────────────────────────────

async def test_timer_start(rest):
    """timer.start sets state to 'active'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tm_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("timer", "start", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "active"


async def test_timer_pause(rest):
    """timer.pause sets state to 'paused'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tm_p_{tag}"
    await rest.set_state(eid, "active")

    await rest.call_service("timer", "pause", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_timer_cancel(rest):
    """timer.cancel sets state to 'idle'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tm_c_{tag}"
    await rest.set_state(eid, "active")

    await rest.call_service("timer", "cancel", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_timer_finish(rest):
    """timer.finish sets state to 'idle'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tm_f_{tag}"
    await rest.set_state(eid, "active")

    await rest.call_service("timer", "finish", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_timer_lifecycle(rest):
    """Full timer lifecycle: idle → active → paused → active → idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tm_lc_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("timer", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "active"

    await rest.call_service("timer", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("timer", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "active"

    await rest.call_service("timer", "cancel", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


# ── Input Number ────────────────────────────────────────────

async def test_input_number_set_value(rest):
    """input_number.set_value stores numeric value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.in_{tag}"
    await rest.set_state(eid, "0")

    await rest.call_service("input_number", "set_value", {
        "entity_id": eid,
        "value": 42,
    })
    state = await rest.get_state(eid)
    assert "42" in state["state"]


async def test_input_number_set_float(rest):
    """input_number.set_value handles float values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.inf_{tag}"
    await rest.set_state(eid, "0")

    await rest.call_service("input_number", "set_value", {
        "entity_id": eid,
        "value": 3.14,
    })
    state = await rest.get_state(eid)
    assert "3.14" in state["state"]


# ── Input Text ──────────────────────────────────────────────

async def test_input_text_set_value(rest):
    """input_text.set_value stores string value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_text.it_{tag}"
    await rest.set_state(eid, "")

    await rest.call_service("input_text", "set_value", {
        "entity_id": eid,
        "value": f"Hello {tag}",
    })
    state = await rest.get_state(eid)
    assert state["state"] == f"Hello {tag}"


async def test_input_text_set_empty(rest):
    """input_text.set_value with empty string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_text.ite_{tag}"
    await rest.set_state(eid, "previous")

    await rest.call_service("input_text", "set_value", {
        "entity_id": eid,
        "value": "",
    })
    state = await rest.get_state(eid)
    assert state["state"] == ""


# ── Input Select ────────────────────────────────────────────

async def test_input_select_select_option(rest):
    """input_select.select_option stores selected option."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_select.is_{tag}"
    await rest.set_state(eid, "option_a")

    await rest.call_service("input_select", "select_option", {
        "entity_id": eid,
        "option": "option_b",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "option_b"


# ── Input Boolean ───────────────────────────────────────────

async def test_input_boolean_toggle(rest):
    """input_boolean.toggle flips state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ib_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"

    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_input_boolean_turn_on_off(rest):
    """input_boolean.turn_on and turn_off set state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ibo_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("input_boolean", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("input_boolean", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
