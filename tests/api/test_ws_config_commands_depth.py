"""
CTS -- WS Config/Registry Command Depth Tests

Tests WS-specific commands: get_config, config/entity_registry/list,
config/entity_registry/update, config/area_registry/* CRUD,
config/label_registry/* CRUD, config/device_registry/list,
lovelace/config, and subscribe_trigger.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── get_config ─────────────────────────────────────────────

async def test_ws_get_config_succeeds(ws):
    """WS get_config returns success."""
    result = await ws.send_command("get_config")
    assert result["success"] is True


async def test_ws_get_config_has_location(ws):
    """WS get_config has location_name."""
    result = await ws.send_command("get_config")
    config = result["result"]
    assert "location_name" in config


async def test_ws_get_config_has_coordinates(ws):
    """WS get_config has latitude and longitude."""
    result = await ws.send_command("get_config")
    config = result["result"]
    assert "latitude" in config
    assert "longitude" in config
    assert isinstance(config["latitude"], (int, float))


async def test_ws_get_config_has_version(ws):
    """WS get_config has version field."""
    result = await ws.send_command("get_config")
    config = result["result"]
    assert "version" in config


async def test_ws_get_config_has_state(ws):
    """WS get_config has state: RUNNING."""
    result = await ws.send_command("get_config")
    config = result["result"]
    assert config.get("state") == "RUNNING"


# ── config/entity_registry/list ────────────────────────────

async def test_ws_entity_registry_list(ws, rest):
    """WS entity_registry/list returns entity entries."""
    await rest.set_state("sensor.ws_ereg_test", "val")
    result = await ws.send_command("config/entity_registry/list")
    assert result["success"] is True
    entries = result["result"]
    assert isinstance(entries, list)
    ids = [e["entity_id"] for e in entries]
    assert "sensor.ws_ereg_test" in ids


async def test_ws_entity_registry_entry_has_fields(ws, rest):
    """Entity registry entries have entity_id, name, platform."""
    await rest.set_state("sensor.ws_ereg_fields", "v", {
        "friendly_name": "Test Fields"
    })
    result = await ws.send_command("config/entity_registry/list")
    entries = result["result"]
    entry = next(e for e in entries if e["entity_id"] == "sensor.ws_ereg_fields")
    assert "name" in entry
    assert "platform" in entry


# ── config/entity_registry/update ──────────────────────────

async def test_ws_entity_registry_update_name(ws, rest):
    """WS entity_registry/update can change friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_erupd_{tag}"
    await rest.set_state(eid, "val")

    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name="Updated Name",
    )
    assert result["success"] is True

    state = await rest.get_state(eid)
    assert state["attributes"].get("friendly_name") == "Updated Name"


async def test_ws_entity_registry_update_icon(ws, rest):
    """WS entity_registry/update can set icon attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_ericon_{tag}"
    await rest.set_state(eid, "val")

    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        icon="mdi:thermometer",
    )
    assert result["success"] is True

    state = await rest.get_state(eid)
    assert state["attributes"].get("icon") == "mdi:thermometer"


async def test_ws_entity_registry_update_nonexistent(ws):
    """WS entity_registry/update on nonexistent entity fails."""
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.does_not_exist_xyz",
        name="Ghost",
    )
    assert result["success"] is False


# ── config/area_registry CRUD ──────────────────────────────

async def test_ws_area_registry_create(ws):
    """WS area_registry/create creates area."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "config/area_registry/create",
        area_id=f"ws_area_{tag}",
        name=f"WS Area {tag}",
    )
    assert result["success"] is True


async def test_ws_area_registry_list(ws):
    """WS area_registry/list returns areas."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/area_registry/create",
        area_id=f"ws_area_list_{tag}",
        name="List Area",
    )
    result = await ws.send_command("config/area_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)


async def test_ws_area_registry_update(ws):
    """WS area_registry/update modifies area name."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/area_registry/create",
        area_id=f"ws_area_upd_{tag}",
        name="Old Name",
    )
    result = await ws.send_command(
        "config/area_registry/update",
        area_id=f"ws_area_upd_{tag}",
        name="New Name",
    )
    assert result["success"] is True


async def test_ws_area_registry_delete(ws):
    """WS area_registry/delete removes area."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/area_registry/create",
        area_id=f"ws_area_del_{tag}",
        name="Delete Me",
    )
    result = await ws.send_command(
        "config/area_registry/delete",
        area_id=f"ws_area_del_{tag}",
    )
    assert result["success"] is True


async def test_ws_area_create_empty_id_fails(ws):
    """WS area_registry/create with empty area_id fails."""
    result = await ws.send_command(
        "config/area_registry/create",
        area_id="",
        name="No ID",
    )
    assert result["success"] is False


# ── config/label_registry CRUD ─────────────────────────────

async def test_ws_label_registry_create(ws):
    """WS label_registry/create creates label."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "config/label_registry/create",
        label_id=f"ws_lbl_{tag}",
        name=f"WS Label {tag}",
        color="#ff0000",
    )
    assert result["success"] is True


async def test_ws_label_registry_list(ws):
    """WS label_registry/list returns labels."""
    result = await ws.send_command("config/label_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)


async def test_ws_label_registry_delete(ws):
    """WS label_registry/delete removes label."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/label_registry/create",
        label_id=f"ws_lbl_del_{tag}",
        name="Delete Label",
    )
    result = await ws.send_command(
        "config/label_registry/delete",
        label_id=f"ws_lbl_del_{tag}",
    )
    assert result["success"] is True


# ── config/device_registry/list ────────────────────────────

async def test_ws_device_registry_list(ws):
    """WS device_registry/list returns devices."""
    result = await ws.send_command("config/device_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)


# ── lovelace/config ────────────────────────────────────────

async def test_ws_lovelace_config(ws):
    """WS lovelace/config returns stub config."""
    result = await ws.send_command("lovelace/config")
    assert result["success"] is True
    config = result["result"]
    assert "views" in config
    assert "title" in config


# ── subscribe_trigger ──────────────────────────────────────

async def test_ws_subscribe_trigger(ws):
    """WS subscribe_trigger returns success (stub)."""
    result = await ws.send_command("subscribe_trigger")
    assert result["success"] is True


# ── Unknown command ────────────────────────────────────────

async def test_ws_unknown_command_fails(ws):
    """WS unknown command returns success: false."""
    result = await ws.send_command("totally_fake_command_xyz")
    assert result["success"] is False
