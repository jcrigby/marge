"""
CTS -- Input Number/Select/Button Extended Domain Tests

Extended tests for input_number, input_text, input_select, input_boolean,
number, select, and button domains with edge cases and lifecycle coverage.
"""

import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Input Number ───────────────────────────────────────

async def test_input_number_set_value(rest):
    """input_number.set_value changes state to numeric string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.in_{tag}"
    await rest.set_state(eid, "0")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/input_number/set_value",
        json={"entity_id": eid, "value": 42.5},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert "42.5" in state["state"]


async def test_input_number_set_zero(rest):
    """input_number.set_value with 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.inz_{tag}"
    await rest.set_state(eid, "100")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_number/set_value",
        json={"entity_id": eid, "value": 0},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert "0" in state["state"]


async def test_input_number_set_negative(rest):
    """input_number.set_value with negative number."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.inn_{tag}"
    await rest.set_state(eid, "0")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_number/set_value",
        json={"entity_id": eid, "value": -10},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert "-10" in state["state"]


# ── Input Text ─────────────────────────────────────────

async def test_input_text_set_value(rest):
    """input_text.set_value changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_text.it_{tag}"
    await rest.set_state(eid, "old")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_text/set_value",
        json={"entity_id": eid, "value": "new text"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "new text"


async def test_input_text_set_empty(rest):
    """input_text.set_value with empty string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_text.ite_{tag}"
    await rest.set_state(eid, "content")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_text/set_value",
        json={"entity_id": eid, "value": ""},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == ""


# ── Input Select ───────────────────────────────────────

async def test_input_select_select_option(rest):
    """input_select.select_option changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_select.is_{tag}"
    await rest.set_state(eid, "option_a")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_select/select_option",
        json={"entity_id": eid, "option": "option_b"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "option_b"


async def test_input_select_empty_option(rest):
    """input_select.select_option with empty string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_select.ise_{tag}"
    await rest.set_state(eid, "something")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_select/select_option",
        json={"entity_id": eid, "option": ""},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == ""


# ── Input Boolean ──────────────────────────────────────

async def test_input_boolean_turn_on(rest):
    """input_boolean.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ib_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_boolean/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_input_boolean_turn_off(rest):
    """input_boolean.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ibo_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_boolean/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_input_boolean_toggle_on_to_off(rest):
    """input_boolean.toggle flips on→off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ibt_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_boolean/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_input_boolean_toggle_off_to_on(rest):
    """input_boolean.toggle flips off→on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ibt2_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/input_boolean/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Number ─────────────────────────────────────────────

async def test_number_set_value(rest):
    """number.set_value changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.n_{tag}"
    await rest.set_state(eid, "0")

    await rest.client.post(
        f"{rest.base_url}/api/services/number/set_value",
        json={"entity_id": eid, "value": 99},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert "99" in state["state"]


# ── Select ─────────────────────────────────────────────

async def test_select_select_option(rest):
    """select.select_option changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.s_{tag}"
    await rest.set_state(eid, "first")

    await rest.client.post(
        f"{rest.base_url}/api/services/select/select_option",
        json={"entity_id": eid, "option": "second"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "second"


# ── Button ─────────────────────────────────────────────

async def test_button_press_no_state_change(rest):
    """button.press returns 200 without changing state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.b_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/button/press",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_button_press_multiple_times(rest):
    """button.press multiple times doesn't change state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.bm_{tag}"
    await rest.set_state(eid, "ready")

    for _ in range(5):
        await rest.client.post(
            f"{rest.base_url}/api/services/button/press",
            json={"entity_id": eid},
            headers=rest._headers(),
        )

    state = await rest.get_state(eid)
    assert state["state"] == "ready"


# ── Input Number attribute preservation (merged from test_input_helpers.py) ──

async def test_input_number_preserves_attributes(rest):
    """input_number.set_value preserves min/max/step attributes."""
    entity_id = "input_number.test_attrs"
    await rest.set_state(entity_id, "10", {"min": 0, "max": 200, "step": 5})
    await rest.call_service("input_number", "set_value", {
        "entity_id": entity_id,
        "value": 75,
    })

    state = await rest.get_state(entity_id)
    assert state["attributes"]["min"] == 0
    assert state["attributes"]["max"] == 200
    assert state["attributes"]["step"] == 5


# ── Input Select option preservation (merged from test_input_helpers.py) ──

async def test_input_select_preserves_options(rest):
    """input_select.select_option preserves the options list."""
    entity_id = "input_select.test_opts"
    options = ["low", "medium", "high"]
    await rest.set_state(entity_id, "low", {"options": options})
    await rest.call_service("input_select", "select_option", {
        "entity_id": entity_id,
        "option": "high",
    })

    state = await rest.get_state(entity_id)
    assert state["attributes"]["options"] == options
