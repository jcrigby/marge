"""
CTS -- Siren Lifecycle Depth Tests

Tests siren domain services: turn_on, turn_off, toggle,
attribute preservation, and full lifecycle.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_siren_turn_on(rest):
    """siren.turn_on → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sld_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_siren_turn_off(rest):
    """siren.turn_off → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sld_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("siren", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_siren_toggle_on_to_off(rest):
    """siren.toggle from on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sld_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_siren_toggle_off_to_on(rest):
    """siren.toggle from off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sld_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_siren_preserves_attrs(rest):
    """Siren services preserve attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sld_attr_{tag}"
    await rest.set_state(eid, "off", {"tone": "alarm"})
    await rest.call_service("siren", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["tone"] == "alarm"


async def test_siren_full_lifecycle(rest):
    """Siren: off → on → toggle → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sld_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("siren", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"

    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("siren", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
