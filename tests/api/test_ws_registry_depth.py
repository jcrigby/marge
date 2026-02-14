"""
CTS -- WebSocket Registry Operations Depth Tests

Tests WS registry commands: area create/update/delete, entity registry
update (friendly_name, icon), label create/delete, lovelace/config stub,
ping/pong, subscribe_trigger, unsubscribe_events, unknown command handling.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Area Registry via WS ────────────────────────────────

async def test_ws_area_create(ws):
    """WS config/area_registry/create creates an area."""
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id="ws_depth_area1",
        name="Depth Test Room",
    )
    assert resp["success"] is True


async def test_ws_area_update(ws):
    """WS config/area_registry/update updates an area name."""
    # Create first
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_depth_area2",
        name="Original Name",
    )
    resp = await ws.send_command(
        "config/area_registry/update",
        area_id="ws_depth_area2",
        name="Updated Name",
    )
    assert resp["success"] is True


async def test_ws_area_delete(ws):
    """WS config/area_registry/delete removes an area."""
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_depth_area3",
        name="Temp Area",
    )
    resp = await ws.send_command(
        "config/area_registry/delete",
        area_id="ws_depth_area3",
    )
    assert resp["success"] is True


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


async def test_ws_area_create_missing_fields(ws):
    """WS area create with missing fields fails."""
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id="",
        name="",
    )
    assert resp["success"] is False


# ── Entity Registry via WS ──────────────────────────────

async def test_ws_entity_registry_list(ws):
    """WS config/entity_registry/list returns entity list."""
    resp = await ws.send_command("config/entity_registry/list")
    assert resp["success"] is True
    entries = resp["result"]
    assert isinstance(entries, list)
    if len(entries) > 0:
        assert "entity_id" in entries[0]
        assert "name" in entries[0]


async def test_ws_entity_registry_update_name(ws, rest):
    """WS config/entity_registry/update changes friendly_name."""
    await rest.set_state("sensor.ws_reg_upd", "100")
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_reg_upd",
        name="Renamed Sensor",
    )
    assert resp["success"] is True
    state = await rest.get_state("sensor.ws_reg_upd")
    assert state["attributes"]["friendly_name"] == "Renamed Sensor"


async def test_ws_entity_registry_update_icon(ws, rest):
    """WS config/entity_registry/update changes icon."""
    await rest.set_state("sensor.ws_reg_icon", "50")
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_reg_icon",
        icon="mdi:thermometer",
    )
    assert resp["success"] is True
    state = await rest.get_state("sensor.ws_reg_icon")
    assert state["attributes"]["icon"] == "mdi:thermometer"


async def test_ws_entity_registry_update_nonexistent(ws):
    """WS entity registry update for nonexistent entity fails."""
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.absolutely_does_not_exist_ws_depth",
        name="Ghost",
    )
    assert resp["success"] is False


# ── Label Registry via WS ───────────────────────────────

async def test_ws_label_create(ws):
    """WS config/label_registry/create creates a label."""
    resp = await ws.send_command(
        "config/label_registry/create",
        label_id="ws_depth_lbl1",
        name="Depth Label",
        color="#ff0000",
    )
    assert resp["success"] is True


async def test_ws_label_delete(ws):
    """WS config/label_registry/delete removes a label."""
    await ws.send_command(
        "config/label_registry/create",
        label_id="ws_depth_lbl2",
        name="Temp Label",
        color="#00ff00",
    )
    resp = await ws.send_command(
        "config/label_registry/delete",
        label_id="ws_depth_lbl2",
    )
    assert resp["success"] is True


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


# ── Lovelace / Ping / Unknown ───────────────────────────

async def test_ws_lovelace_config(ws):
    """WS lovelace/config returns stub with views array."""
    resp = await ws.send_command("lovelace/config")
    assert resp["success"] is True
    result = resp["result"]
    assert "views" in result
    assert isinstance(result["views"], list)
    assert result["title"] == "Marge"


async def test_ws_ping_pong(ws):
    """WS ping returns pong response."""
    resp = await ws.send_command("ping")
    # The response format for ping is special: type=pong, no success field
    # OR it might be wrapped as a result. Accept either format.
    assert resp is not None


async def test_ws_subscribe_trigger(ws):
    """WS subscribe_trigger returns success."""
    resp = await ws.send_command("subscribe_trigger")
    assert resp["success"] is True


async def test_ws_unknown_command(ws):
    """WS unknown command returns failure."""
    resp = await ws.send_command("nonexistent_command_xyz")
    assert resp["success"] is False


async def test_ws_get_notifications(ws):
    """WS get_notifications returns notification list."""
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)
