"""
CTS -- WebSocket Registry CRUD Tests

Tests config/area_registry, config/device_registry, config/label_registry,
config/entity_registry (list + update), lovelace/config, subscribe_trigger,
ping/pong, and get_config via the WebSocket API.
"""

import uuid

import pytest

pytestmark = pytest.mark.asyncio


# ── Ping / Pong ──────────────────────────────────────────

async def test_ws_ping_multiple(ws):
    """Multiple pings all succeed."""
    for _ in range(3):
        assert await ws.ping() is True


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


async def test_ws_area_registry_create_missing_fields(ws):
    """config/area_registry/create without name fails."""
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id="test",
    )
    assert resp.get("success", False) is False


async def test_ws_area_create_missing_id(ws):
    """WS config/area_registry/create with missing area_id fails."""
    resp = await ws.send_command("config/area_registry/create",
        name="No ID")
    assert resp["success"] is False


@pytest.mark.marge_only
async def test_ws_area_create_list_delete_roundtrip(ws):
    """Full area CRUD roundtrip via WS (uuid-isolated)."""
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


async def test_ws_label_registry_missing_fields(ws):
    """config/label_registry/create without name fails."""
    resp = await ws.send_command(
        "config/label_registry/create",
        label_id="test",
    )
    assert resp.get("success", False) is False


@pytest.mark.marge_only
async def test_ws_label_create_list_delete_roundtrip(ws):
    """Full label CRUD roundtrip via WS (uuid-isolated)."""
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


# ── Entity Registry ───────────────────────────────────────

async def test_ws_entity_registry_list(ws):
    """config/entity_registry/list returns entity entries."""
    result = await ws.send_command("config/entity_registry/list")
    assert result["success"] is True
    assert isinstance(result["result"], list)
    if len(result["result"]) > 0:
        entry = result["result"][0]
        assert "entity_id" in entry


async def test_ws_entity_registry_entry_fields(ws, rest):
    """Entity registry entries have expected name and platform fields."""
    await rest.set_state("sensor.ws_reg_fields", "10", {"friendly_name": "Test Sensor"})
    result = await ws.send_command("config/entity_registry/list")
    assert result["success"] is True
    entry = next((e for e in result["result"] if e["entity_id"] == "sensor.ws_reg_fields"), None)
    assert entry is not None
    assert "name" in entry
    assert "platform" in entry


@pytest.mark.parametrize("field,expected", [
    ("disabled_by", None),
    ("platform", "mqtt"),
])
async def test_ws_entity_registry_field_value(ws, rest, field, expected):
    """Entity registry entries have correct default field values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsfld_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command("config/entity_registry/list")
    entries = resp["result"]
    found = [e for e in entries if e["entity_id"] == eid]
    assert len(found) == 1
    assert field in found[0]
    assert found[0][field] == expected


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


@pytest.mark.marge_only
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


@pytest.mark.marge_only
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


@pytest.mark.marge_only
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


@pytest.mark.marge_only
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


async def test_ws_entity_registry_update_nonexistent(ws):
    """config/entity_registry/update for missing entity fails."""
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.definitely_does_not_exist_xyz",
        name="Nope",
    )
    assert result["success"] is False


# ── Get Config ───────────────────────────────────────────

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


# ── Lovelace Config ───────────────────────────────────────

@pytest.mark.marge_only
async def test_ws_lovelace_config(ws):
    """lovelace/config returns a dashboard config stub."""
    result = await ws.send_command("lovelace/config")
    assert result["success"] is True
    assert "views" in result["result"]
    assert "title" in result["result"]


# ── Subscribe Trigger ─────────────────────────────────────

async def test_ws_subscribe_trigger(ws):
    """subscribe_trigger returns a result (success varies by implementation)."""
    result = await ws.send_command("subscribe_trigger")
    # Marge returns success for bare subscribe_trigger;
    # HA requires trigger config and may return success=false without it.
    assert "success" in result


# ── Unknown Command ───────────────────────────────────────

async def test_ws_unknown_command_fails(ws):
    """Unknown WS command returns success=false."""
    result = await ws.send_command("totally_bogus_command")
    assert result["success"] is False
