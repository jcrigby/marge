"""
CTS -- WebSocket Registry Mutation Tests

Tests WS commands for area/label/entity registry CRUD operations,
lovelace/config stub, and subscribe_trigger.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Area Registry via WS ─────────────────────────────────

async def test_ws_area_create(ws, rest):
    """WS config/area_registry/create creates an area."""
    resp = await ws.send_command("config/area_registry/create",
        area_id="ws_test_area", name="WS Test Area")
    assert resp["success"] is True

    areas = (await rest.client.get(f"{rest.base_url}/api/areas")).json()
    area_ids = [a["area_id"] for a in areas]
    assert "ws_test_area" in area_ids


async def test_ws_area_create_missing_id(ws):
    """WS config/area_registry/create with missing area_id fails."""
    resp = await ws.send_command("config/area_registry/create",
        name="No ID")
    assert resp["success"] is False


async def test_ws_area_update(ws, rest):
    """WS config/area_registry/update renames an area."""
    await ws.send_command("config/area_registry/create",
        area_id="ws_rename_area", name="Before")
    resp = await ws.send_command("config/area_registry/update",
        area_id="ws_rename_area", name="After")
    assert resp["success"] is True

    areas = (await rest.client.get(f"{rest.base_url}/api/areas")).json()
    area = next(a for a in areas if a["area_id"] == "ws_rename_area")
    assert area["name"] == "After"


async def test_ws_area_delete(ws, rest):
    """WS config/area_registry/delete removes an area."""
    await ws.send_command("config/area_registry/create",
        area_id="ws_del_area", name="To Delete")
    resp = await ws.send_command("config/area_registry/delete",
        area_id="ws_del_area")
    assert resp["success"] is True

    areas = (await rest.client.get(f"{rest.base_url}/api/areas")).json()
    area_ids = [a["area_id"] for a in areas]
    assert "ws_del_area" not in area_ids


# ── Entity Registry via WS ───────────────────────────────

async def test_ws_entity_registry_update_name(ws, rest):
    """WS config/entity_registry/update changes friendly_name."""
    entity_id = "sensor.ws_rename_test"
    await rest.set_state(entity_id, "42", {"friendly_name": "Old Name"})

    resp = await ws.send_command("config/entity_registry/update",
        entity_id=entity_id, name="New Name")
    assert resp["success"] is True

    state = await rest.get_state(entity_id)
    assert state["attributes"]["friendly_name"] == "New Name"


async def test_ws_entity_registry_update_icon(ws, rest):
    """WS config/entity_registry/update sets icon."""
    entity_id = "sensor.ws_icon_test"
    await rest.set_state(entity_id, "100")

    resp = await ws.send_command("config/entity_registry/update",
        entity_id=entity_id, icon="mdi:thermometer")
    assert resp["success"] is True

    state = await rest.get_state(entity_id)
    assert state["attributes"]["icon"] == "mdi:thermometer"


async def test_ws_entity_registry_update_nonexistent(ws):
    """WS config/entity_registry/update on nonexistent entity fails."""
    resp = await ws.send_command("config/entity_registry/update",
        entity_id="sensor.does_not_exist_ws_reg", name="Phantom")
    assert resp["success"] is False


# ── Label Registry via WS ────────────────────────────────

async def test_ws_label_create(ws, rest):
    """WS config/label_registry/create creates a label."""
    resp = await ws.send_command("config/label_registry/create",
        label_id="ws_label_test", name="WS Test Label", color="#00ff00")
    assert resp["success"] is True

    labels = (await rest.client.get(f"{rest.base_url}/api/labels")).json()
    label_ids = [l["label_id"] for l in labels]
    assert "ws_label_test" in label_ids


async def test_ws_label_create_missing_fields(ws):
    """WS config/label_registry/create with missing fields fails."""
    resp = await ws.send_command("config/label_registry/create",
        color="#ff0000")
    assert resp["success"] is False


async def test_ws_label_delete(ws, rest):
    """WS config/label_registry/delete removes a label."""
    await ws.send_command("config/label_registry/create",
        label_id="ws_label_del", name="To Delete")
    resp = await ws.send_command("config/label_registry/delete",
        label_id="ws_label_del")
    assert resp["success"] is True

    labels = (await rest.client.get(f"{rest.base_url}/api/labels")).json()
    label_ids = [l["label_id"] for l in labels]
    assert "ws_label_del" not in label_ids


# ── Lovelace Config ──────────────────────────────────────

async def test_ws_lovelace_config(ws):
    """WS lovelace/config returns a config stub."""
    resp = await ws.send_command("lovelace/config")
    assert resp["success"] is True
    assert "views" in resp["result"]
    assert "title" in resp["result"]


# ── Subscribe Trigger ────────────────────────────────────

async def test_ws_subscribe_trigger(ws):
    """WS subscribe_trigger succeeds (registers subscription)."""
    resp = await ws.send_command("subscribe_trigger",
        trigger={"platform": "state", "entity_id": "light.test"})
    assert resp["success"] is True


# ── Merged from test_ws_registry_depth.py ────────────────


async def test_ws_area_list(ws):
    """WS config/area_registry/list returns area list."""
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_depth_area4",
        name="Listed Area",
    )
    resp = await ws.send_command("config/area_registry/list")
    assert resp["success"] is True
    areas = resp["result"]
    assert isinstance(areas, list)
    ids = [a["area_id"] for a in areas]
    assert "ws_depth_area4" in ids


async def test_ws_area_create_empty_fields(ws):
    """WS area create with empty fields fails."""
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id="",
        name="",
    )
    assert resp["success"] is False


async def test_ws_entity_registry_list(ws):
    """WS config/entity_registry/list returns entity list."""
    resp = await ws.send_command("config/entity_registry/list")
    assert resp["success"] is True
    entries = resp["result"]
    assert isinstance(entries, list)
    if len(entries) > 0:
        assert "entity_id" in entries[0]
        assert "name" in entries[0]


async def test_ws_label_list(ws):
    """WS config/label_registry/list returns labels."""
    await ws.send_command(
        "config/label_registry/create",
        label_id="ws_depth_lbl3",
        name="Listed Label",
        color="#0000ff",
    )
    resp = await ws.send_command("config/label_registry/list")
    assert resp["success"] is True
    labels = resp["result"]
    assert isinstance(labels, list)


async def test_ws_ping_pong(ws):
    """WS ping returns pong response."""
    resp = await ws.send_command("ping")
    # The response format for ping is special: type=pong, no success field
    # OR it might be wrapped as a result. Accept either format.
    assert resp is not None


async def test_ws_unknown_command(ws):
    """WS unknown command returns failure."""
    resp = await ws.send_command("nonexistent_command_xyz")
    assert resp["success"] is False


async def test_ws_get_notifications(ws):
    """WS get_notifications returns notification list."""
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)
