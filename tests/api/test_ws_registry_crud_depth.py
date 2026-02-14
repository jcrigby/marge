"""
CTS -- WebSocket Registry CRUD Depth Tests

Tests WebSocket registry commands: config/entity_registry/update,
config/area_registry/create/update/delete,
config/label_registry/create/delete, and config/device_registry/list.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Entity Registry ──────────────────────────────────────

async def test_entity_registry_list(ws):
    """config/entity_registry/list returns entity entries."""
    resp = await ws.send_command("config/entity_registry/list")
    assert resp["success"] is True
    result = resp["result"]
    assert isinstance(result, list)


async def test_entity_registry_entry_format(ws, rest):
    """Entity registry entries have entity_id, name, platform."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.reg_fmt_{tag}"
    await rest.set_state(eid, "val", {"friendly_name": f"Reg {tag}"})

    resp = await ws.send_command("config/entity_registry/list")
    entries = resp["result"]
    entry = next((e for e in entries if e["entity_id"] == eid), None)
    assert entry is not None
    assert "name" in entry
    assert "platform" in entry


async def test_entity_registry_update_name(ws, rest):
    """config/entity_registry/update changes friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.reg_upd_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name=f"Updated Name {tag}",
    )
    assert resp["success"] is True

    state = await rest.get_state(eid)
    assert state["attributes"].get("friendly_name") == f"Updated Name {tag}"


async def test_entity_registry_update_icon(ws, rest):
    """config/entity_registry/update sets icon attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.reg_icon_{tag}"
    await rest.set_state(eid, "val")

    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        icon="mdi:thermometer",
    )
    assert resp["success"] is True

    state = await rest.get_state(eid)
    assert state["attributes"].get("icon") == "mdi:thermometer"


async def test_entity_registry_update_nonexistent(ws):
    """Updating nonexistent entity returns failure."""
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.absolutely_nonexistent_999",
        name="Doesn't Matter",
    )
    assert resp["success"] is False


# ── Area Registry ────────────────────────────────────────

async def test_area_registry_create(ws):
    """config/area_registry/create creates an area."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id=f"area_{tag}",
        name=f"Test Area {tag}",
    )
    assert resp["success"] is True


async def test_area_registry_list_after_create(ws):
    """config/area_registry/list shows created area."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/area_registry/create",
        area_id=f"area_list_{tag}",
        name=f"Listed {tag}",
    )

    resp = await ws.send_command("config/area_registry/list")
    assert resp["success"] is True
    areas = resp["result"]
    assert isinstance(areas, list)
    area_ids = [a.get("area_id") for a in areas]
    assert f"area_list_{tag}" in area_ids


async def test_area_registry_update(ws):
    """config/area_registry/update renames an area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_upd_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name=f"Original {tag}",
    )

    resp = await ws.send_command(
        "config/area_registry/update",
        area_id=aid,
        name=f"Renamed {tag}",
    )
    assert resp["success"] is True


async def test_area_registry_delete(ws):
    """config/area_registry/delete removes an area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_del_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name=f"Deletable {tag}",
    )

    resp = await ws.send_command(
        "config/area_registry/delete",
        area_id=aid,
    )
    assert resp["success"] is True


async def test_area_create_empty_fails(ws):
    """Creating area with empty area_id fails."""
    resp = await ws.send_command(
        "config/area_registry/create",
        area_id="",
        name="",
    )
    assert resp["success"] is False


# ── Label Registry ───────────────────────────────────────

async def test_label_registry_create(ws):
    """config/label_registry/create creates a label."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "config/label_registry/create",
        label_id=f"label_{tag}",
        name=f"Test Label {tag}",
        color="#ff0000",
    )
    assert resp["success"] is True


async def test_label_registry_list(ws):
    """config/label_registry/list returns labels."""
    tag = uuid.uuid4().hex[:8]
    await ws.send_command(
        "config/label_registry/create",
        label_id=f"label_list_{tag}",
        name=f"Listed {tag}",
    )

    resp = await ws.send_command("config/label_registry/list")
    assert resp["success"] is True
    labels = resp["result"]
    assert isinstance(labels, list)
    label_ids = [l.get("label_id") for l in labels]
    assert f"label_list_{tag}" in label_ids


async def test_label_registry_delete(ws):
    """config/label_registry/delete removes a label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"label_del_{tag}"
    await ws.send_command(
        "config/label_registry/create",
        label_id=lid,
        name=f"Deletable {tag}",
    )

    resp = await ws.send_command(
        "config/label_registry/delete",
        label_id=lid,
    )
    assert resp["success"] is True


async def test_label_create_empty_fails(ws):
    """Creating label with empty label_id fails."""
    resp = await ws.send_command(
        "config/label_registry/create",
        label_id="",
        name="",
    )
    assert resp["success"] is False


# ── Device Registry ──────────────────────────────────────

async def test_device_registry_list(ws):
    """config/device_registry/list returns devices list."""
    resp = await ws.send_command("config/device_registry/list")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)
