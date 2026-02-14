"""
CTS -- Number, Select, Text, Button Services Depth Tests

Tests number.set_value, select.select_option, text.set_value,
and button.press domain services with attribute preservation.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Number ──────────────────────────────────────────────

async def test_number_set_value_integer(rest):
    """number.set_value with integer."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.nstb_int_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("number", "set_value", {
        "entity_id": eid, "value": 42,
    })
    state = await rest.get_state(eid)
    assert "42" in state["state"]


async def test_number_set_value_float(rest):
    """number.set_value with float."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.nstb_flt_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("number", "set_value", {
        "entity_id": eid, "value": 3.14,
    })
    state = await rest.get_state(eid)
    assert "3.14" in state["state"]


async def test_number_set_value_preserves_attrs(rest):
    """number.set_value preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.nstb_nattr_{tag}"
    await rest.set_state(eid, "50", {"min": 0, "max": 100, "step": 1})
    await rest.call_service("number", "set_value", {
        "entity_id": eid, "value": 75,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["min"] == 0
    assert state["attributes"]["max"] == 100


# ── Select ──────────────────────────────────────────────

async def test_select_select_option(rest):
    """select.select_option sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.nstb_opt_{tag}"
    await rest.set_state(eid, "option_a")
    await rest.call_service("select", "select_option", {
        "entity_id": eid, "option": "option_b",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "option_b"


async def test_select_select_option_preserves_attrs(rest):
    """select.select_option preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.nstb_oattr_{tag}"
    await rest.set_state(eid, "low", {"options": ["low", "medium", "high"]})
    await rest.call_service("select", "select_option", {
        "entity_id": eid, "option": "high",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "high"
    assert state["attributes"]["options"] == ["low", "medium", "high"]


# ── Text ────────────────────────────────────────────────

async def test_text_set_value(rest):
    """text.set_value sets state to string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.nstb_txt_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("text", "set_value", {
        "entity_id": eid, "value": "hello world",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "hello world"


async def test_text_set_value_empty(rest):
    """text.set_value with empty string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.nstb_txte_{tag}"
    await rest.set_state(eid, "something")
    await rest.call_service("text", "set_value", {
        "entity_id": eid, "value": "",
    })
    state = await rest.get_state(eid)
    assert state["state"] == ""


async def test_text_set_value_preserves_attrs(rest):
    """text.set_value preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.nstb_tattr_{tag}"
    await rest.set_state(eid, "old", {"max_length": 255})
    await rest.call_service("text", "set_value", {
        "entity_id": eid, "value": "new",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "new"
    assert state["attributes"]["max_length"] == 255


# ── Button ──────────────────────────────────────────────

async def test_button_press_returns_success(rest):
    """button.press succeeds (no state change)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.nstb_btn_{tag}"
    await rest.set_state(eid, "unknown")
    # button.press returns None (no state change), but service call succeeds
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/button/press",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    assert resp.status_code == 200


async def test_button_press_preserves_state(rest):
    """button.press does not change entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.nstb_btnp_{tag}"
    await rest.set_state(eid, "2024-01-01T00:00:00")
    await rest.client.post(
        f"{rest.base_url}/api/services/button/press",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    state = await rest.get_state(eid)
    assert state["state"] == "2024-01-01T00:00:00"
