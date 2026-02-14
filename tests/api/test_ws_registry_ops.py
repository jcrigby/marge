"""
CTS -- WebSocket Registry Operation Tests

Tests WS commands for registry management: entity_registry/list,
entity_registry/update, area CRUD, label CRUD, device_registry/list,
ping/pong, subscribe_trigger, lovelace/config, get_notifications.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Ping / Pong ──────────────────────────────────────────

async def test_ws_ping_returns_pong(ws):
    """WS ping command returns pong response."""
    result = await ws.ping()
    assert result is True


async def test_ws_ping_multiple(ws):
    """Multiple pings all succeed."""
    for _ in range(3):
        assert await ws.ping() is True


# ── Entity Registry ─────────────────────────────────────

async def test_ws_entity_registry_list(ws, rest):
    """config/entity_registry/list returns entity entries."""
    await rest.set_state("sensor.ws_reg_list_test", "42")
    result = await ws.send_command("config/entity_registry/list")
    assert result["success"] is True
    entries = result["result"]
    assert isinstance(entries, list)
    assert len(entries) > 0
    ids = [e["entity_id"] for e in entries]
    assert "sensor.ws_reg_list_test" in ids


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


async def test_ws_entity_registry_update_icon(ws, rest):
    """config/entity_registry/update sets icon attribute."""
    await rest.set_state("sensor.ws_reg_icon", "0")
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_reg_icon",
        icon="mdi:thermometer",
    )
    assert result["success"] is True
    state = await rest.get_state("sensor.ws_reg_icon")
    assert state["attributes"]["icon"] == "mdi:thermometer"


async def test_ws_entity_registry_update_nonexistent(ws):
    """config/entity_registry/update fails for missing entity."""
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_reg_nonexistent_xyz",
        name="Test",
    )
    assert result["success"] is False


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


# ── Device Registry via WS ──────────────────────────────

async def test_ws_device_registry_list(ws):
    """config/device_registry/list returns devices."""
    result = await ws.send_command("config/device_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)


# ── Lovelace Config ─────────────────────────────────────

async def test_ws_lovelace_config(ws):
    """lovelace/config returns stub config."""
    result = await ws.send_command("lovelace/config")
    assert result["success"] is True
    config = result["result"]
    assert "views" in config
    assert "title" in config


# ── Subscribe Trigger ───────────────────────────────────

async def test_ws_subscribe_trigger(ws):
    """subscribe_trigger returns success."""
    result = await ws.send_command("subscribe_trigger")
    assert result["success"] is True


# ── Get Notifications ───────────────────────────────────

async def test_ws_get_notifications(ws):
    """get_notifications returns list."""
    result = await ws.send_command("get_notifications")
    assert result["success"] is True
    assert isinstance(result["result"], list)


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


# ── Entity Registry Update with Area ────────────────────

async def test_ws_entity_update_area_assignment(ws, rest):
    """config/entity_registry/update assigns entity to area."""
    await rest.set_state("sensor.ws_reg_area", "0")
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_ent_area",
        name="Entity Area",
    )
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_reg_area",
        area_id="ws_ent_area",
    )
    assert result["success"] is True
