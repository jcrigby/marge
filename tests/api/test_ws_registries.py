"""
CTS -- WebSocket Registry CRUD Tests

Tests config/area_registry, config/device_registry, config/label_registry,
config/entity_registry/update, lovelace/config, and subscribe_trigger
via the WebSocket API.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Area Registry ─────────────────────────────────────────

async def test_ws_area_registry_list(ws):
    """config/area_registry/list returns a list."""
    result = await ws.send_command("config/area_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)


async def test_ws_area_registry_create(ws):
    """config/area_registry/create adds a new area."""
    result = await ws.send_command(
        "config/area_registry/create",
        area_id="ws_test_area",
        name="WS Test Area",
    )
    assert result["success"] is True

    # Verify it appears in the list
    listing = await ws.send_command("config/area_registry/list")
    ids = [a["area_id"] for a in listing["result"]]
    assert "ws_test_area" in ids


async def test_ws_area_registry_update(ws):
    """config/area_registry/update renames an area."""
    # Create first
    await ws.send_command(
        "config/area_registry/create",
        area_id="ws_update_area",
        name="Before",
    )

    # Update
    result = await ws.send_command(
        "config/area_registry/update",
        area_id="ws_update_area",
        name="After",
    )
    assert result["success"] is True

    # Verify
    listing = await ws.send_command("config/area_registry/list")
    area = next(a for a in listing["result"] if a["area_id"] == "ws_update_area")
    assert area["name"] == "After"


async def test_ws_area_registry_delete(ws):
    """config/area_registry/delete removes an area."""
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

    listing = await ws.send_command("config/area_registry/list")
    ids = [a["area_id"] for a in listing["result"]]
    assert "ws_del_area" not in ids


async def test_ws_area_create_empty_fails(ws):
    """config/area_registry/create with empty fields fails."""
    result = await ws.send_command(
        "config/area_registry/create",
        area_id="",
        name="",
    )
    assert result["success"] is False


# ── Device Registry ───────────────────────────────────────

async def test_ws_device_registry_list(ws):
    """config/device_registry/list returns a list."""
    result = await ws.send_command("config/device_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)


async def test_ws_device_registry_entry_format(ws):
    """Device registry entries have expected fields."""
    result = await ws.send_command("config/device_registry/list")
    assert result["success"] is True
    if len(result["result"]) > 0:
        entry = result["result"][0]
        assert "id" in entry
        assert "name" in entry


# ── Label Registry ────────────────────────────────────────

async def test_ws_label_registry_list(ws):
    """config/label_registry/list returns a list."""
    result = await ws.send_command("config/label_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)


async def test_ws_label_registry_create(ws):
    """config/label_registry/create adds a label."""
    result = await ws.send_command(
        "config/label_registry/create",
        label_id="ws_test_label",
        name="WS Label",
        color="#ff0000",
    )
    assert result["success"] is True

    listing = await ws.send_command("config/label_registry/list")
    ids = [l["label_id"] for l in listing["result"]]
    assert "ws_test_label" in ids


async def test_ws_label_registry_delete(ws):
    """config/label_registry/delete removes a label."""
    await ws.send_command(
        "config/label_registry/create",
        label_id="ws_del_label",
        name="Del Label",
        color="#000",
    )

    result = await ws.send_command(
        "config/label_registry/delete",
        label_id="ws_del_label",
    )
    assert result["success"] is True

    listing = await ws.send_command("config/label_registry/list")
    ids = [l["label_id"] for l in listing["result"]]
    assert "ws_del_label" not in ids


async def test_ws_label_create_empty_fails(ws):
    """config/label_registry/create with empty fields fails."""
    result = await ws.send_command(
        "config/label_registry/create",
        label_id="",
        name="",
    )
    assert result["success"] is False


# ── Entity Registry ───────────────────────────────────────

async def test_ws_entity_registry_list(ws):
    """config/entity_registry/list returns entity entries."""
    result = await ws.send_command("config/entity_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)
    if len(result["result"]) > 0:
        entry = result["result"][0]
        assert "entity_id" in entry


async def test_ws_entity_registry_update_name(ws, rest):
    """config/entity_registry/update renames an entity."""
    await rest.set_state("sensor.ws_rename_test", "42", {"friendly_name": "Old Name"})

    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_rename_test",
        name="New Name",
    )
    assert result["success"] is True

    # Verify via REST
    state = await rest.get_state("sensor.ws_rename_test")
    assert state["attributes"]["friendly_name"] == "New Name"


async def test_ws_entity_registry_update_icon(ws, rest):
    """config/entity_registry/update sets icon attribute."""
    await rest.set_state("sensor.ws_icon_test", "50")

    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.ws_icon_test",
        icon="mdi:thermometer",
    )
    assert result["success"] is True

    state = await rest.get_state("sensor.ws_icon_test")
    assert state["attributes"]["icon"] == "mdi:thermometer"


async def test_ws_entity_registry_update_nonexistent(ws):
    """config/entity_registry/update for missing entity fails."""
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.definitely_does_not_exist_xyz",
        name="Nope",
    )
    assert result["success"] is False


# ── Lovelace Config ───────────────────────────────────────

async def test_ws_lovelace_config(ws):
    """lovelace/config returns a dashboard config stub."""
    result = await ws.send_command("lovelace/config")
    assert result["success"] is True
    assert "views" in result["result"]
    assert "title" in result["result"]


# ── Subscribe Trigger ─────────────────────────────────────

async def test_ws_subscribe_trigger(ws):
    """subscribe_trigger returns success."""
    result = await ws.send_command("subscribe_trigger")
    assert result["success"] is True


# ── Unknown Command ───────────────────────────────────────

async def test_ws_unknown_command_fails(ws):
    """Unknown WS command returns success=false."""
    result = await ws.send_command("totally_bogus_command")
    assert result["success"] is False
