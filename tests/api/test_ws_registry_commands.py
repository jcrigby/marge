"""
CTS -- WebSocket Registry Commands Depth Tests

Tests WS-only registry commands: entity_registry/list, entity_registry/update,
area_registry (CRUD), device_registry/list, label_registry (CRUD),
lovelace/config, get_services, subscribe_trigger.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_entity_registry_list(ws, rest):
    """config/entity_registry/list returns entity entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsreg_{tag}"
    await rest.set_state(eid, "val", {"friendly_name": "WS Reg Test"})

    resp = await ws.send_command("config/entity_registry/list")
    assert resp.get("success", False) is True
    entries = resp["result"]
    assert isinstance(entries, list)
    found = [e for e in entries if e["entity_id"] == eid]
    assert len(found) == 1
    assert found[0]["name"] == "WS Reg Test"
    assert found[0]["platform"] == "mqtt"


async def test_ws_entity_registry_update_name(ws, rest):
    """config/entity_registry/update changes friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsupdate_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name="New Friendly Name",
    )
    assert resp.get("success", False) is True

    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == "New Friendly Name"


async def test_ws_entity_registry_update_icon(ws, rest):
    """config/entity_registry/update sets icon attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsicon_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        icon="mdi:thermometer",
    )
    assert resp.get("success", False) is True

    state = await rest.get_state(eid)
    assert state["attributes"]["icon"] == "mdi:thermometer"


async def test_ws_entity_registry_update_nonexistent(ws):
    """config/entity_registry/update on nonexistent entity fails."""
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.does_not_exist_99999",
        name="Nothing",
    )
    assert resp.get("success", False) is False


async def test_ws_area_registry_create(ws):
    """config/area_registry/create creates an area."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id=f"ws_area_{tag}",
        name=f"WS Area {tag}",
    )
    assert resp.get("success", False) is True


async def test_ws_area_registry_list(ws):
    """config/area_registry/list returns areas."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/area_registry/create",
        area_id=f"wslist_{tag}",
        name=f"WS List {tag}",
    )

    resp = await ws.send_command("config/area_registry/list")
    assert resp.get("success", False) is True
    areas = resp["result"]
    assert isinstance(areas, list)
    found = [a for a in areas if a.get("area_id") == f"wslist_{tag}"]
    assert len(found) == 1


async def test_ws_area_registry_update(ws):
    """config/area_registry/update renames an area."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/area_registry/create",
        area_id=f"wsup_{tag}",
        name="Old Name",
    )

    resp = await ws.send_command(
        "config/area_registry/update",
        area_id=f"wsup_{tag}",
        name="New Name",
    )
    assert resp.get("success", False) is True


async def test_ws_area_registry_delete(ws):
    """config/area_registry/delete removes an area."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/area_registry/create",
        area_id=f"wsdel_{tag}",
        name="Delete Me",
    )

    resp = await ws.send_command(
        "config/area_registry/delete",
        area_id=f"wsdel_{tag}",
    )
    assert resp.get("success", False) is True


async def test_ws_area_registry_create_missing_fields(ws):
    """config/area_registry/create without name fails."""
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id="test",
    )
    assert resp.get("success", False) is False


async def test_ws_device_registry_list(ws):
    """config/device_registry/list returns device entries."""
    resp = await ws.send_command("config/device_registry/list")
    assert resp.get("success", False) is True
    assert isinstance(resp["result"], list)


async def test_ws_label_registry_create(ws):
    """config/label_registry/create creates a label."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "config/label_registry/create",
        label_id=f"wslbl_{tag}",
        name=f"Label {tag}",
        color="blue",
    )
    assert resp.get("success", False) is True


async def test_ws_label_registry_list(ws):
    """config/label_registry/list returns labels."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/label_registry/create",
        label_id=f"wslbll_{tag}",
        name=f"List Label {tag}",
    )

    resp = await ws.send_command("config/label_registry/list")
    assert resp.get("success", False) is True
    labels = resp["result"]
    assert isinstance(labels, list)


async def test_ws_label_registry_delete(ws):
    """config/label_registry/delete removes a label."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/label_registry/create",
        label_id=f"wslbld_{tag}",
        name=f"Del Label {tag}",
    )

    resp = await ws.send_command(
        "config/label_registry/delete",
        label_id=f"wslbld_{tag}",
    )
    assert resp.get("success", False) is True


async def test_ws_label_registry_missing_fields(ws):
    """config/label_registry/create without name fails."""
    resp = await ws.send_command(
        "config/label_registry/create",
        label_id="test",
    )
    assert resp.get("success", False) is False


async def test_ws_lovelace_config(ws):
    """lovelace/config returns minimal stub."""
    resp = await ws.send_command("lovelace/config")
    assert resp.get("success", False) is True
    config = resp["result"]
    assert "views" in config
    assert "title" in config
    assert config["title"] == "Marge"


async def test_ws_get_services(ws):
    """get_services returns domain-grouped service listing."""
    resp = await ws.send_command("get_services")
    assert resp.get("success", False) is True
    result = resp["result"]
    assert isinstance(result, list)
    domains = [entry["domain"] for entry in result]
    assert "light" in domains
    assert "switch" in domains
    assert "lock" in domains


async def test_ws_get_services_has_service_names(ws):
    """get_services includes service names per domain."""
    resp = await ws.send_command("get_services")
    result = resp["result"]
    light = next(e for e in result if e["domain"] == "light")
    assert "turn_on" in light["services"]
    assert "turn_off" in light["services"]
    assert "toggle" in light["services"]


async def test_ws_subscribe_trigger(ws):
    """subscribe_trigger returns success."""
    resp = await ws.send_command("subscribe_trigger")
    assert resp.get("success", False) is True


async def test_ws_get_notifications(ws):
    """get_notifications returns notification list."""
    resp = await ws.send_command("get_notifications")
    assert resp.get("success", False) is True
    assert isinstance(resp["result"], list)
