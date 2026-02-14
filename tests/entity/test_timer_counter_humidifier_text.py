"""
CTS -- Timer, Counter, Humidifier, Text, Input Datetime Domain Services

Tests service handlers for less-common domains: timer (start/pause/cancel/finish),
counter (increment/decrement/reset), humidifier (on/off/toggle/set_humidity/set_mode),
text (set_value), and input_datetime (set_datetime).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Timer ──────────────────────────────────────────────

async def test_timer_start(rest):
    """timer.start sets state to active."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.t_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/timer/start",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "active"


async def test_timer_pause(rest):
    """timer.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tp_{tag}"
    await rest.set_state(eid, "active")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/timer/pause",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_timer_cancel(rest):
    """timer.cancel sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tc_{tag}"
    await rest.set_state(eid, "active")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/timer/cancel",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_timer_finish(rest):
    """timer.finish sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"timer.tf_{tag}"
    await rest.set_state(eid, "active")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/timer/finish",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "idle"


# ── Counter ────────────────────────────────────────────

async def test_counter_increment(rest):
    """counter.increment adds 1 to current value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.c_{tag}"
    await rest.set_state(eid, "5")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/counter/increment",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "6"


async def test_counter_decrement(rest):
    """counter.decrement subtracts 1 from current value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.cd_{tag}"
    await rest.set_state(eid, "10")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/counter/decrement",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "9"


async def test_counter_reset_with_initial(rest):
    """counter.reset sets to initial attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.cr_{tag}"
    await rest.set_state(eid, "42", {"initial": 0})

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/counter/reset",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "0"


async def test_counter_reset_default_zero(rest):
    """counter.reset defaults to 0 without initial attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.crz_{tag}"
    await rest.set_state(eid, "99")

    await rest.client.post(
        f"{rest.base_url}/api/services/counter/reset",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "0"


async def test_counter_increment_from_zero(rest):
    """counter.increment from 0 gives 1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.c0_{tag}"
    await rest.set_state(eid, "0")

    await rest.client.post(
        f"{rest.base_url}/api/services/counter/increment",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "1"


async def test_counter_decrement_below_zero(rest):
    """counter.decrement below zero gives negative."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.cn_{tag}"
    await rest.set_state(eid, "0")

    await rest.client.post(
        f"{rest.base_url}/api/services/counter/decrement",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "-1"


# ── Humidifier ─────────────────────────────────────────

async def test_humidifier_turn_on(rest):
    """humidifier.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.h_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/humidifier/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_humidifier_turn_off(rest):
    """humidifier.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.ho_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/humidifier/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_humidifier_toggle(rest):
    """humidifier.toggle flips on↔off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.ht_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/humidifier/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_humidifier_set_humidity(rest):
    """humidifier.set_humidity stores humidity attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hh_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/humidifier/set_humidity",
        json={"entity_id": eid, "humidity": 55},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["humidity"] == 55


async def test_humidifier_set_mode(rest):
    """humidifier.set_mode stores mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hm_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/humidifier/set_mode",
        json={"entity_id": eid, "mode": "silent"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["mode"] == "silent"


# ── Text ───────────────────────────────────────────────

async def test_text_set_value(rest):
    """text.set_value changes entity state to provided value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.t_{tag}"
    await rest.set_state(eid, "old")

    await rest.client.post(
        f"{rest.base_url}/api/services/text/set_value",
        json={"entity_id": eid, "value": "new text"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "new text"


async def test_text_set_empty_value(rest):
    """text.set_value with empty string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.te_{tag}"
    await rest.set_state(eid, "content")

    await rest.client.post(
        f"{rest.base_url}/api/services/text/set_value",
        json={"entity_id": eid, "value": ""},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == ""


# ── Input Datetime ─────────────────────────────────────

async def test_input_datetime_set_datetime(rest):
    """input_datetime.set_datetime sets state to provided datetime string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.dt_{tag}"
    await rest.set_state(eid, "unknown")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_datetime/set_datetime",
        json={"entity_id": eid, "datetime": "2026-02-13T08:30:00"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "2026-02-13T08:30:00"


async def test_input_datetime_set_date(rest):
    """input_datetime.set_datetime with date field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.dd_{tag}"
    await rest.set_state(eid, "unknown")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_datetime/set_datetime",
        json={"entity_id": eid, "date": "2026-02-13"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "2026-02-13"


async def test_input_datetime_set_time(rest):
    """input_datetime.set_datetime with time field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.dt2_{tag}"
    await rest.set_state(eid, "unknown")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_datetime/set_datetime",
        json={"entity_id": eid, "time": "14:30:00"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "14:30:00"
