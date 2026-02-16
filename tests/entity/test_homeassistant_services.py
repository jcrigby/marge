"""
CTS -- Group and Update Domain Entity Tests

Tests group.set and update.install services.
"""

import pytest

pytestmark = pytest.mark.asyncio


# -- Group domain --

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


# -- Update domain --

async def test_update_install(rest):
    """update.install sets state to 'installing'."""
    entity_id = "update.test_update"
    await rest.set_state(entity_id, "available")
    await rest.call_service("update", "install", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "installing"
