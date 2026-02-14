"""
CTS -- Miscellaneous Service Depth Tests

Tests remaining service domains: timer (start/pause/cancel/finish),
counter (increment/decrement/reset with initial), group.set, update
(install/skip), text.set_value, lock.open, input_datetime.set_datetime,
climate.turn_on/turn_off, water_heater turn_on/turn_off, valve lifecycle.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Timer ─────────────────────────────────────────────────

async def test_timer_start(rest):
    """timer.start sets state to active."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tmr_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("timer", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "active"


async def test_timer_pause(rest):
    """timer.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tmr_p_{tag}"
    await rest.set_state(eid, "active")
    await rest.call_service("timer", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"


async def test_timer_cancel(rest):
    """timer.cancel sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tmr_c_{tag}"
    await rest.set_state(eid, "active")
    await rest.call_service("timer", "cancel", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


async def test_timer_finish(rest):
    """timer.finish sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tmr_f_{tag}"
    await rest.set_state(eid, "active")
    await rest.call_service("timer", "finish", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


async def test_timer_lifecycle(rest):
    """Timer: idle → active → paused → active → finish → idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tmr_life_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("timer", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "active"

    await rest.call_service("timer", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("timer", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "active"

    await rest.call_service("timer", "finish", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


# ── Counter ───────────────────────────────────────────────

async def test_counter_increment(rest):
    """counter.increment increases state by 1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ctr_{tag}"
    await rest.set_state(eid, "5")
    await rest.call_service("counter", "increment", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "6"


async def test_counter_decrement(rest):
    """counter.decrement decreases state by 1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ctr_d_{tag}"
    await rest.set_state(eid, "10")
    await rest.call_service("counter", "decrement", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "9"


async def test_counter_reset_with_initial(rest):
    """counter.reset resets to initial attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ctr_r_{tag}"
    await rest.set_state(eid, "42", {"initial": 10})
    await rest.call_service("counter", "reset", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "10"


async def test_counter_reset_default_zero(rest):
    """counter.reset without initial defaults to 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ctr_r0_{tag}"
    await rest.set_state(eid, "99")
    await rest.call_service("counter", "reset", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "0"


async def test_counter_multi_increment(rest):
    """Counter: 0 → increment 3 times → 3."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ctr_multi_{tag}"
    await rest.set_state(eid, "0")
    for _ in range(3):
        await rest.call_service("counter", "increment", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "3"


async def test_counter_negative(rest):
    """Counter can go negative via decrement."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ctr_neg_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("counter", "decrement", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "-1"


# ── Group ─────────────────────────────────────────────────

async def test_group_set_on(rest):
    """group.set sets state from data."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.grp_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("group", "set", {
        "entity_id": eid, "state": "on",
    })
    assert (await rest.get_state(eid))["state"] == "on"


async def test_group_set_custom_state(rest):
    """group.set with custom state string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.grp_c_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("group", "set", {
        "entity_id": eid, "state": "home",
    })
    assert (await rest.get_state(eid))["state"] == "home"


# ── Update ────────────────────────────────────────────────

async def test_update_install(rest):
    """update.install sets state to installing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"update.upd_{tag}"
    await rest.set_state(eid, "available")
    await rest.call_service("update", "install", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "installing"


async def test_update_skip(rest):
    """update.skip sets state to skipped."""
    tag = uuid.uuid4().hex[:8]
    eid = f"update.upd_s_{tag}"
    await rest.set_state(eid, "available")
    await rest.call_service("update", "skip", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "skipped"


# ── Text ──────────────────────────────────────────────────

async def test_text_set_value(rest):
    """text.set_value sets state to the value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.txt_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("text", "set_value", {
        "entity_id": eid, "value": "hello world",
    })
    assert (await rest.get_state(eid))["state"] == "hello world"


# ── Lock open ─────────────────────────────────────────────

async def test_lock_open(rest):
    """lock.open sets state to open (distinct from unlock)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.lk_open_{tag}"
    await rest.set_state(eid, "locked")
    await rest.call_service("lock", "open", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"


# ── Input Datetime ────────────────────────────────────────

async def test_input_datetime_set_datetime(rest):
    """input_datetime.set_datetime sets state to datetime string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.idt_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid, "datetime": "2026-02-14 08:30:00",
    })
    assert (await rest.get_state(eid))["state"] == "2026-02-14 08:30:00"


async def test_input_datetime_set_date(rest):
    """input_datetime.set_datetime with date field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.idt_d_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid, "date": "2026-03-01",
    })
    assert (await rest.get_state(eid))["state"] == "2026-03-01"


async def test_input_datetime_set_time(rest):
    """input_datetime.set_datetime with time field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.idt_t_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid, "time": "15:30:00",
    })
    assert (await rest.get_state(eid))["state"] == "15:30:00"


# ── Climate turn_on/turn_off ─────────────────────────────

async def test_climate_turn_on(rest):
    """climate.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.clim_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("climate", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_climate_turn_off(rest):
    """climate.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.clim_off_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


# ── Water Heater turn_on/turn_off ────────────────────────

async def test_water_heater_turn_on(rest):
    """water_heater.turn_on sets state to eco."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.wh_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("water_heater", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "eco"


async def test_water_heater_turn_off(rest):
    """water_heater.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.wh_off_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


# ── Valve lifecycle ───────────────────────────────────────

async def test_valve_open(rest):
    """valve.open_valve sets state to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlv_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "open_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"


async def test_valve_close(rest):
    """valve.close_valve sets state to closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlv_c_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("valve", "close_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_valve_toggle(rest):
    """valve.toggle flips open ↔ closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlv_t_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_valve_lifecycle(rest):
    """Valve: closed → open → toggle → closed → toggle → open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlv_life_{tag}"
    await rest.set_state(eid, "closed")

    await rest.call_service("valve", "open_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"

    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"

    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"

    await rest.call_service("valve", "close_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"
