"""
CTS -- WS Registry Relationships Depth Tests

Tests cross-registry relationships via WebSocket: device-to-entity
mappings, entity registry listing, device registry field presence,
label-to-entity mappings, area-to-entity relationships, and
lovelace/config stubbing.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Entity Registry ──────────────────────────────────────

async def test_ws_entity_registry_list_success(rest, ws):
    """WS config/entity_registry/list returns success."""
    result = await ws.send_command("config/entity_registry/list")
    assert result["success"] is True


async def test_ws_entity_registry_list_is_array(rest, ws):
    """WS entity_registry/list returns an array."""
    result = await ws.send_command("config/entity_registry/list")
    assert isinstance(result["result"], list)


async def test_ws_entity_registry_contains_created_entity(rest, ws):
    """Entity created via REST appears in entity registry."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wrr_ereg_{tag}"
    await rest.set_state(eid, "100")

    result = await ws.send_command("config/entity_registry/list")
    eids = [e["entity_id"] for e in result["result"]]
    assert eid in eids


async def test_ws_entity_registry_entry_has_fields(rest, ws):
    """Entity registry entry has entity_id, name, platform, disabled_by."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wrr_fields_{tag}"
    await rest.set_state(eid, "1", {"friendly_name": "Test Sensor"})

    result = await ws.send_command("config/entity_registry/list")
    entry = next(e for e in result["result"] if e["entity_id"] == eid)
    assert "entity_id" in entry
    assert "platform" in entry
    assert "disabled_by" in entry


async def test_ws_entity_registry_friendly_name(rest, ws):
    """Entity registry picks up friendly_name from attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wrr_fname_{tag}"
    await rest.set_state(eid, "1", {"friendly_name": "My Test Sensor"})

    result = await ws.send_command("config/entity_registry/list")
    entry = next(e for e in result["result"] if e["entity_id"] == eid)
    assert entry["name"] == "My Test Sensor"


# ── Device Registry ──────────────────────────────────────

async def test_ws_device_registry_list_success(ws):
    """WS config/device_registry/list returns success."""
    result = await ws.send_command("config/device_registry/list")
    assert result["success"] is True


async def test_ws_device_registry_list_is_array(ws):
    """WS device_registry/list returns an array."""
    result = await ws.send_command("config/device_registry/list")
    assert isinstance(result["result"], list)


# ── Area Registry ────────────────────────────────────────

async def test_ws_area_registry_list_success(ws):
    """WS config/area_registry/list returns success."""
    result = await ws.send_command("config/area_registry/list")
    assert result["success"] is True


async def test_ws_area_create_and_list(ws):
    """WS area create then list shows the area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_wrr_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name=f"Test Area {tag}",
    )

    result = await ws.send_command("config/area_registry/list")
    area_ids = [a["area_id"] for a in result["result"]]
    assert aid in area_ids


async def test_ws_area_update_name(ws):
    """WS area update changes the name."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_wrr_upd_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name="Original",
    )
    await ws.send_command(
        "config/area_registry/update",
        area_id=aid,
        name="Updated Name",
    )

    result = await ws.send_command("config/area_registry/list")
    area = next(a for a in result["result"] if a["area_id"] == aid)
    assert area["name"] == "Updated Name"


async def test_ws_area_delete_removes(ws):
    """WS area delete removes area from list."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_wrr_del_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name="Temp Area",
    )
    await ws.send_command(
        "config/area_registry/delete",
        area_id=aid,
    )

    result = await ws.send_command("config/area_registry/list")
    area_ids = [a["area_id"] for a in result["result"]]
    assert aid not in area_ids


# ── Label Registry ───────────────────────────────────────

async def test_ws_label_registry_list_success(ws):
    """WS config/label_registry/list returns success."""
    result = await ws.send_command("config/label_registry/list")
    assert result["success"] is True


async def test_ws_label_create_and_list(ws):
    """WS label create then list shows the label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_wrr_{tag}"
    await ws.send_command(
        "config/label_registry/create",
        label_id=lid,
        name=f"Test Label {tag}",
        color="#FF0000",
    )

    result = await ws.send_command("config/label_registry/list")
    label_ids = [l["label_id"] for l in result["result"]]
    assert lid in label_ids
