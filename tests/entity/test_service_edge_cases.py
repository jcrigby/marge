"""
CTS -- Service Call Edge Cases

Tests service call edge cases: missing entity_id, nonexistent entity,
wrong domain service, multiple entity_id array, attribute preservation
across service calls, and domain-specific service arguments.
"""

import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_service_call_nonexistent_entity(rest):
    """Service call on nonexistent entity still returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": f"light.nonexist_{tag}"},
        headers=rest._headers(),
    )
    # Marge returns 200 even if entity doesn't exist (matches HA behavior)
    assert resp.status_code == 200


async def test_service_call_empty_entity_id(rest):
    """Service call with empty entity_id returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": ""},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_light_turn_on_preserves_brightness(rest):
    """Turning light on preserves brightness attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pres_{tag}"
    await rest.set_state(eid, "off", {"brightness": 200})

    await rest.call_service("light", "turn_on", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 200


async def test_light_turn_on_sets_brightness(rest):
    """Turning light on with brightness sets the attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.brt_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 128,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 128


async def test_light_turn_on_sets_color_temp(rest):
    """Turning light on with color_temp sets the attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ct_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "color_temp": 350,
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("color_temp") == 350


async def test_light_turn_on_sets_rgb(rest):
    """Turning light on with rgb_color sets the attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.rgb_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "rgb_color": [255, 0, 128],
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("rgb_color") == [255, 0, 128]


async def test_climate_set_temperature(rest):
    """Climate set_temperature stores temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.temp_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 72,
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("temperature") == 72


async def test_climate_set_hvac_mode(rest):
    """Climate set_hvac_mode changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid,
        "hvac_mode": "cool",
    })

    state = await rest.get_state(eid)
    assert state["state"] == "cool"


async def test_fan_set_percentage(rest):
    """Fan set_percentage updates speed and state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.pct_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid,
        "percentage": 75,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("percentage") == 75


async def test_fan_set_percentage_zero_turns_off(rest):
    """Fan set_percentage(0) turns fan off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.zero_{tag}"
    await rest.set_state(eid, "on", {"percentage": 50})

    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid,
        "percentage": 0,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_cover_open_close(rest):
    """Cover open/close changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.oc_{tag}"
    await rest.set_state(eid, "closed")

    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"

    await rest.call_service("cover", "close_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_cover_set_position(rest):
    """Cover set_cover_position sets position attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.pos_{tag}"
    await rest.set_state(eid, "closed")

    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid,
        "position": 50,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"].get("current_position") == 50


async def test_cover_set_position_zero_closes(rest):
    """Cover set_cover_position(0) closes cover."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.z_{tag}"
    await rest.set_state(eid, "open", {"current_position": 100})

    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid,
        "position": 0,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_lock_lock_unlock(rest):
    """Lock lock/unlock toggles state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.lu_{tag}"
    await rest.set_state(eid, "unlocked")

    await rest.call_service("lock", "lock", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "locked"

    await rest.call_service("lock", "unlock", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "unlocked"


async def test_number_set_value(rest):
    """Number set_value stores numeric state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.nv_{tag}"
    await rest.set_state(eid, "0")

    await rest.call_service("number", "set_value", {
        "entity_id": eid,
        "value": 42,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "42"


async def test_select_select_option(rest):
    """Select select_option changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.opt_{tag}"
    await rest.set_state(eid, "option_a")

    await rest.call_service("select", "select_option", {
        "entity_id": eid,
        "option": "option_b",
    })

    state = await rest.get_state(eid)
    assert state["state"] == "option_b"


async def test_toggle_generic_entity(rest):
    """Generic toggle works on switch."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.tgl_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("switch", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"

    await rest.call_service("switch", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_service_call_multiple_entities(rest):
    """Service call with entity_id array affects all entities."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.multi_{tag}_{i}" for i in range(3)]

    # Pre-create all off
    for eid in eids:
        await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eids,
    })

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on"


async def test_input_boolean_toggle(rest):
    """Input boolean toggle works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ib_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
