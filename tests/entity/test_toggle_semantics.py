"""
CTS -- Toggle Semantics Tests

Verifies that toggle service consistently flips state between
on/off (or open/closed) for all domains that support it.
"""

import asyncio
import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_light_toggle_on_to_off(rest):
    """light.toggle: on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tog_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("light", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_light_toggle_off_to_on(rest):
    """light.toggle: off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_switch_toggle_roundtrip(rest):
    """switch.toggle: off → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_fan_toggle_roundtrip(rest):
    """fan.toggle: off → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("fan", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_siren_toggle_roundtrip(rest):
    """siren.toggle: off → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_cover_toggle_roundtrip(rest):
    """cover.toggle: closed → open → closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.tog_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("cover", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"
    await rest.call_service("cover", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_valve_toggle_roundtrip(rest):
    """valve.toggle: closed → open → closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"valve.tog_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"
    await rest.call_service("valve", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_humidifier_toggle_roundtrip(rest):
    """humidifier.toggle: off → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_input_boolean_toggle_roundtrip(rest):
    """input_boolean.toggle: off → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_homeassistant_toggle_roundtrip(rest):
    """homeassistant.toggle: off → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_generic_fallback_toggle(rest):
    """Toggle on unknown domain uses generic fallback."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom_domain.tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("custom_domain", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
