"""
CTS -- homeassistant Domain Service Tests

Tests homeassistant.turn_on, turn_off, toggle across multiple domains,
and homeassistant.restart/check_config service calls.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_ha_turn_on(rest):
    """homeassistant.turn_on sets entity to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_on_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ha_turn_off(rest):
    """homeassistant.turn_off sets entity to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_off_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ha_toggle(rest):
    """homeassistant.toggle flips entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_toggle_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ha_turn_on_multiple(rest):
    """homeassistant.turn_on with entity_id array."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.ha_multi_{tag}_{i}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/turn_on",
        json={"entity_id": eids},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_ha_turn_off_multiple(rest):
    """homeassistant.turn_off with entity_id array."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.ha_off_multi_{tag}_{i}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/turn_off",
        json={"entity_id": eids},
        headers=rest._headers(),
    )

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "off"


async def test_ha_toggle_mixed_states(rest):
    """homeassistant.toggle with mixed on/off entities."""
    tag = uuid.uuid4().hex[:8]
    eid_on = f"light.ha_tmix_on_{tag}"
    eid_off = f"light.ha_tmix_off_{tag}"
    await rest.set_state(eid_on, "on")
    await rest.set_state(eid_off, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/toggle",
        json={"entity_id": [eid_on, eid_off]},
        headers=rest._headers(),
    )

    s_on = await rest.get_state(eid_on)
    s_off = await rest.get_state(eid_off)
    assert s_on["state"] == "off"
    assert s_off["state"] == "on"


async def test_ha_turn_on_different_domains(rest):
    """homeassistant.turn_on works across different domains."""
    tag = uuid.uuid4().hex[:8]
    entities = {
        f"light.ha_dom_{tag}": "off",
        f"switch.ha_dom_{tag}": "off",
        f"fan.ha_dom_{tag}": "off",
    }
    for eid, state in entities.items():
        await rest.set_state(eid, state)

    for eid in entities:
        await rest.client.post(
            f"{rest.base_url}/api/services/homeassistant/turn_on",
            json={"entity_id": eid},
            headers=rest._headers(),
        )

    for eid in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_ha_check_config(rest):
    """homeassistant.check_config returns valid."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "valid"


async def test_ha_turn_on_preserves_attributes(rest):
    """homeassistant.turn_on preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_attrs_{tag}"
    await rest.set_state(eid, "off", {"brightness": 200})

    await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 200


# -- Group domain (merged from test_homeassistant_services.py) --

async def test_group_set(rest):
    """group.set sets group state."""
    entity_id = "group.test_group"
    await rest.set_state(entity_id, "off")
    await rest.call_service("group", "set", {
        "entity_id": entity_id,
        "state": "on",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


# -- Update domain (merged from test_homeassistant_services.py) --

async def test_update_install(rest):
    """update.install sets state to 'installing'."""
    entity_id = "update.test_update"
    await rest.set_state(entity_id, "available")
    await rest.call_service("update", "install", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "installing"
