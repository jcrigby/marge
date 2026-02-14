"""
CTS -- Humidifier Service Depth Tests

Tests humidifier domain services: turn_on, turn_off, toggle,
set_humidity, and set_mode with attribute verification.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_humidifier_turn_on(rest):
    """humidifier.turn_on sets state to 'on'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("humidifier", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_humidifier_turn_off(rest):
    """humidifier.turn_off sets state to 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_off_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("humidifier", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_humidifier_toggle(rest):
    """humidifier.toggle flips state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_tog_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_humidifier_set_humidity(rest):
    """humidifier.set_humidity stores humidity attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_h_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid,
        "humidity": 55,
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("humidity") == 55


async def test_humidifier_set_mode(rest):
    """humidifier.set_mode stores mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_m_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid,
        "mode": "auto",
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("mode") == "auto"


async def test_humidifier_lifecycle(rest):
    """Full humidifier lifecycle: off → on → set_humidity → set_mode → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("humidifier", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 40,
    })
    assert (await rest.get_state(eid))["attributes"].get("humidity") == 40

    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "normal",
    })
    assert (await rest.get_state(eid))["attributes"].get("mode") == "normal"

    await rest.call_service("humidifier", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
