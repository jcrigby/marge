"""
CTS -- Switch & Binary Sensor Services Depth Tests

Tests switch domain services (turn_on, turn_off, toggle with
attribute preservation) and binary_sensor state handling
(on/off, device_class, attribute storage).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Switch Turn On/Off ──────────────────────────────────

async def test_switch_turn_on(rest):
    """switch.turn_on → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_switch_turn_off(rest):
    """switch.turn_off → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_switch_toggle_on_to_off(rest):
    """switch.toggle from on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_switch_toggle_off_to_on(rest):
    """switch.toggle from off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


# ── Switch Attribute Preservation ───────────────────────

async def test_switch_turn_on_preserves_attrs(rest):
    """switch.turn_on preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_onattr_{tag}"
    await rest.set_state(eid, "off", {"device_class": "outlet"})
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["device_class"] == "outlet"


async def test_switch_turn_off_preserves_attrs(rest):
    """switch.turn_off preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_offattr_{tag}"
    await rest.set_state(eid, "on", {"icon": "mdi:power"})
    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["icon"] == "mdi:power"


async def test_switch_toggle_preserves_attrs(rest):
    """switch.toggle preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_togattr_{tag}"
    await rest.set_state(eid, "on", {"friendly_name": "My Switch"})
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["friendly_name"] == "My Switch"


# ── Binary Sensor State ────────────────────────────────

async def test_binary_sensor_set_on(rest):
    """binary_sensor can be set to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"binary_sensor.sbsd_on_{tag}"
    await rest.set_state(eid, "on")
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_binary_sensor_set_off(rest):
    """binary_sensor can be set to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"binary_sensor.sbsd_off_{tag}"
    await rest.set_state(eid, "off")
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_binary_sensor_device_class(rest):
    """binary_sensor with device_class attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"binary_sensor.sbsd_dc_{tag}"
    await rest.set_state(eid, "on", {"device_class": "motion"})
    state = await rest.get_state(eid)
    assert state["attributes"]["device_class"] == "motion"


async def test_binary_sensor_toggle_via_set_state(rest):
    """binary_sensor toggled via set_state calls."""
    tag = uuid.uuid4().hex[:8]
    eid = f"binary_sensor.sbsd_toggle_{tag}"
    await rest.set_state(eid, "off")
    assert (await rest.get_state(eid))["state"] == "off"
    await rest.set_state(eid, "on")
    assert (await rest.get_state(eid))["state"] == "on"


# ── Switch Full Lifecycle ───────────────────────────────

async def test_switch_full_lifecycle(rest):
    """Switch: off → on → toggle → on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sbsd_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("switch", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"

    await rest.call_service("switch", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
