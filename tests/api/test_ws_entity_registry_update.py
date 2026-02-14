"""
CTS -- WebSocket Entity Registry Update & Area Assignment Tests

Tests WS config/entity_registry/update with name, icon, and area_id
assignments, plus WS-based area creation/listing roundtrip.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_entity_update_name_and_icon(ws, rest):
    """Update both name and icon in single WS command."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsupd_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name="Updated Name",
        icon="mdi:lightbulb",
    )
    assert resp.get("success", False) is True

    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == "Updated Name"
    assert state["attributes"]["icon"] == "mdi:lightbulb"


async def test_ws_entity_update_area_assignment(ws, rest):
    """Entity registry update with area_id assigns entity to area."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsarea_{tag}"
    aid = f"area_ws_{tag}"

    await rest.set_state(eid, "val")

    # Create area first
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name=f"Room {tag}",
    )

    # Assign entity to area
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        area_id=aid,
    )
    assert resp.get("success", False) is True


async def test_ws_entity_update_clear_area(ws, rest):
    """Clearing area_id unassigns entity from area."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsunarea_{tag}"
    aid = f"area_wsun_{tag}"

    await rest.set_state(eid, "val")
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name=f"Room {tag}",
    )
    await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        area_id=aid,
    )

    # Clear area
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        area_id="",
    )
    assert resp.get("success", False) is True


async def test_ws_entity_update_preserves_state(ws, rest):
    """Entity registry update preserves entity state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wspres_{tag}"
    await rest.set_state(eid, "important_value", {"existing_attr": 42})

    await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name="New Name",
    )

    state = await rest.get_state(eid)
    assert state["state"] == "important_value"
    assert state["attributes"]["existing_attr"] == 42
    assert state["attributes"]["friendly_name"] == "New Name"


async def test_ws_area_create_list_delete_roundtrip(ws):
    """Full area CRUD roundtrip via WS."""
    tag = uuid.uuid4().hex[:8]
    aid = f"wsrt_{tag}"

    # Create
    r1 = await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name=f"Roundtrip {tag}",
    )
    assert r1.get("success", False) is True

    # List and verify
    r2 = await ws.send_command("config/area_registry/list")
    areas = r2["result"]
    found = [a for a in areas if a.get("area_id") == aid]
    assert len(found) == 1
    assert found[0]["name"] == f"Roundtrip {tag}"

    # Delete
    r3 = await ws.send_command(
        "config/area_registry/delete",
        area_id=aid,
    )
    assert r3.get("success", False) is True

    # Verify gone
    r4 = await ws.send_command("config/area_registry/list")
    areas2 = r4["result"]
    found2 = [a for a in areas2 if a.get("area_id") == aid]
    assert len(found2) == 0


async def test_ws_label_create_list_delete_roundtrip(ws):
    """Full label CRUD roundtrip via WS."""
    tag = uuid.uuid4().hex[:8]
    lid = f"wslrt_{tag}"

    # Create
    r1 = await ws.send_command(
        "config/label_registry/create",
        label_id=lid,
        name=f"Label {tag}",
        color="green",
    )
    assert r1.get("success", False) is True

    # List and verify
    r2 = await ws.send_command("config/label_registry/list")
    labels = r2["result"]
    found = [l for l in labels if l.get("label_id") == lid]
    assert len(found) == 1

    # Delete
    r3 = await ws.send_command(
        "config/label_registry/delete",
        label_id=lid,
    )
    assert r3.get("success", False) is True


async def test_ws_entity_registry_has_disabled_by(ws, rest):
    """Entity registry entries have disabled_by field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsdb_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command("config/entity_registry/list")
    entries = resp["result"]
    found = [e for e in entries if e["entity_id"] == eid]
    assert len(found) == 1
    assert "disabled_by" in found[0]
    assert found[0]["disabled_by"] is None


async def test_ws_entity_registry_platform_mqtt(ws, rest):
    """Entity registry entries report platform as mqtt."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsplat_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command("config/entity_registry/list")
    entries = resp["result"]
    found = [e for e in entries if e["entity_id"] == eid]
    assert len(found) == 1
    assert found[0]["platform"] == "mqtt"
