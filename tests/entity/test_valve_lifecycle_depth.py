"""
CTS -- Valve Lifecycle Depth Tests

Tests valve domain services: open_valve, close_valve, toggle,
attribute preservation, and full lifecycle.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_valve_open(rest):
    """valve.open_valve → open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlld_open_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "open_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"


async def test_valve_close(rest):
    """valve.close_valve → closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlld_close_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("valve", "close_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_valve_toggle_open_to_closed(rest):
    """valve.toggle from open → closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlld_tog1_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_valve_toggle_closed_to_open(rest):
    """valve.toggle from closed → open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlld_tog2_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"


async def test_valve_preserves_attrs(rest):
    """Valve services preserve attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlld_attr_{tag}"
    await rest.set_state(eid, "closed", {"device_class": "water"})
    await rest.call_service("valve", "open_valve", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["device_class"] == "water"


async def test_valve_full_lifecycle(rest):
    """Valve: closed → open → toggle → open → close."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.vlld_lc_{tag}"
    await rest.set_state(eid, "closed")

    await rest.call_service("valve", "open_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"

    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"

    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"

    await rest.call_service("valve", "close_valve", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"
