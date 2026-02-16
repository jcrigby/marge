"""
CTS -- WebSocket Registry Operation Tests

Tests WS commands for registry management: entity_registry/list,
entity_registry/update, area CRUD, label CRUD, device_registry/list,
ping/pong, get_config.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Ping / Pong ──────────────────────────────────────────

async def test_ws_ping_multiple(ws):
    """Multiple pings all succeed."""
    for _ in range(3):
        assert await ws.ping() is True


# ── Entity Registry ─────────────────────────────────────

async def test_ws_entity_registry_entry_fields(ws, rest):
    """Entity registry entries have expected fields."""
    await rest.set_state("sensor.ws_reg_fields", "10", {"friendly_name": "Test Sensor"})
    result = await ws.send_command("config/entity_registry/list")
    assert result["success"] is True
    entry = next((e for e in result["result"] if e["entity_id"] == "sensor.ws_reg_fields"), None)
    assert entry is not None
    assert "name" in entry
    assert "platform" in entry


async def test_ws_entity_registry_update(ws, rest):
    """config/entity_registry/update changes friendly_name."""
    await rest.set_state("sensor.ws_reg_upd", "0")
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_reg_upd",
        name="Updated Name",
    )
    assert result["success"] is True
    state = await rest.get_state("sensor.ws_reg_upd")
    assert state["attributes"]["friendly_name"] == "Updated Name"


# ── Area Registry via WS ────────────────────────────────

async def test_ws_area_create(ws):
    """config/area_registry/create via WebSocket."""
    result = await ws.send_command(
        "config/area_registry/create",
        area_id="ws_test_area",
        name="WS Test Area",
    )
    assert result["success"] is True


async def test_ws_area_list(ws):
    """config/area_registry/list returns areas."""
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_list_area",
        name="WS List Area",
    )
    result = await ws.send_command("config/area_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)
    ids = [a.get("area_id") for a in result["result"]]
    assert "ws_list_area" in ids


async def test_ws_area_update(ws):
    """config/area_registry/update renames area."""
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_upd_area",
        name="Original",
    )
    result = await ws.send_command(
        "config/area_registry/update",
        area_id="ws_upd_area",
        name="Renamed",
    )
    assert result["success"] is True


async def test_ws_area_delete(ws):
    """config/area_registry/delete removes area."""
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_del_area",
        name="Delete Me",
    )
    result = await ws.send_command(
        "config/area_registry/delete",
        area_id="ws_del_area",
    )
    assert result["success"] is True


async def test_ws_area_create_missing_fields(ws):
    """config/area_registry/create fails without name."""
    result = await ws.send_command(
        "config/area_registry/create",
        area_id="ws_bad_area",
        name="",
    )
    assert result["success"] is False


# ── Label Registry via WS ───────────────────────────────

async def test_ws_label_create(ws):
    """config/label_registry/create via WebSocket."""
    result = await ws.send_command(
        "config/label_registry/create",
        label_id="ws_test_label",
        name="WS Test Label",
        color="#ff0000",
    )
    assert result["success"] is True


async def test_ws_label_list(ws):
    """config/label_registry/list returns labels."""
    await ws.send_command(
        "config/label_registry/create",
        label_id="ws_list_label",
        name="WS List Label",
        color="#00ff00",
    )
    result = await ws.send_command("config/label_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)
    ids = [l.get("label_id") for l in result["result"]]
    assert "ws_list_label" in ids


async def test_ws_label_delete(ws):
    """config/label_registry/delete removes label."""
    await ws.send_command(
        "config/label_registry/create",
        label_id="ws_del_label",
        name="Delete Label",
        color="",
    )
    result = await ws.send_command(
        "config/label_registry/delete",
        label_id="ws_del_label",
    )
    assert result["success"] is True


async def test_ws_label_create_missing_fields(ws):
    """config/label_registry/create fails without name."""
    result = await ws.send_command(
        "config/label_registry/create",
        label_id="ws_bad_label",
        name="",
    )
    assert result["success"] is False


# ── Get Config ──────────────────────────────────────────

async def test_ws_get_config_fields(ws):
    """get_config returns expected configuration fields."""
    result = await ws.send_command("get_config")
    assert result["success"] is True
    config = result["result"]
    assert "location_name" in config
    assert "latitude" in config
    assert "longitude" in config
    assert "time_zone" in config
    assert "version" in config
    assert "state" in config
    assert config["state"] == "RUNNING"
