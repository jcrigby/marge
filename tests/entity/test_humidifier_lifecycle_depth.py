"""
CTS -- Humidifier Lifecycle Depth Tests

Tests humidifier domain services: turn_on, turn_off, toggle,
set_humidity, set_mode, and full lifecycle scenarios.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Turn On/Off ─────────────────────────────────────────

async def test_humidifier_turn_on(rest):
    """humidifier.turn_on → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("humidifier", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_humidifier_turn_off(rest):
    """humidifier.turn_off → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_humidifier_toggle_on_to_off(rest):
    """humidifier.toggle from on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_humidifier_toggle_off_to_on(rest):
    """humidifier.toggle from off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


# ── Set Humidity ────────────────────────────────────────

async def test_humidifier_set_humidity(rest):
    """humidifier.set_humidity sets humidity attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_hum_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 55,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["humidity"] == 55


async def test_humidifier_set_humidity_preserves_state(rest):
    """humidifier.set_humidity preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_hpres_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 40,
    })
    assert (await rest.get_state(eid))["state"] == "on"


# ── Set Mode ───────────────────────────────────────────

async def test_humidifier_set_mode(rest):
    """humidifier.set_mode sets mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_mode_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "auto",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["mode"] == "auto"


# ── Full Lifecycle ──────────────────────────────────────

async def test_humidifier_full_lifecycle(rest):
    """Humidifier: off → on → set_humidity → set_mode → toggle → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hld_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("humidifier", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 60,
    })
    assert (await rest.get_state(eid))["attributes"]["humidity"] == 60

    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "sleep",
    })
    assert (await rest.get_state(eid))["attributes"]["mode"] == "sleep"

    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
