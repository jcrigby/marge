"""
CTS -- WS Area & Label Registry Depth Tests

Tests WebSocket-based registry operations: area CRUD, label CRUD,
entity registry update with area assignment, and edge cases for
missing/invalid fields.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── WS Area Registry ─────────────────────────────────────

async def test_ws_area_create(ws):
    """WS config/area_registry/create creates an area."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "config/area_registry/create",
        area_id=f"ws_area_{tag}",
        name=f"WS Area {tag}",
    )
    assert result.get("success") is True


async def test_ws_area_update(ws):
    """WS config/area_registry/update updates an area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"ws_area_upd_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name="Before",
    )
    result = await ws.send_command(
        "config/area_registry/update",
        area_id=aid,
        name="After",
    )
    assert result.get("success") is True


async def test_ws_area_delete(ws):
    """WS config/area_registry/delete removes an area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"ws_area_del_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name="To Delete",
    )
    result = await ws.send_command(
        "config/area_registry/delete",
        area_id=aid,
    )
    assert result.get("success") is True


async def test_ws_area_update_missing_id(ws):
    """WS area update with empty area_id fails."""
    result = await ws.send_command(
        "config/area_registry/update",
        area_id="",
        name="Missing ID",
    )
    assert result.get("success") is False


# ── WS Label Registry ────────────────────────────────────

async def test_ws_label_create(ws):
    """WS config/label_registry/create creates a label."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "config/label_registry/create",
        label_id=f"ws_lbl_{tag}",
        name=f"WS Label {tag}",
        color="#ff0000",
    )
    assert result.get("success") is True


async def test_ws_label_delete(ws):
    """WS config/label_registry/delete removes a label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"ws_lbl_del_{tag}"
    await ws.send_command(
        "config/label_registry/create",
        label_id=lid,
        name="To Delete",
    )
    result = await ws.send_command(
        "config/label_registry/delete",
        label_id=lid,
    )
    assert result.get("success") is True


async def test_ws_label_create_missing_fields(ws):
    """WS label create with empty fields fails."""
    result = await ws.send_command(
        "config/label_registry/create",
        label_id="",
        name="",
    )
    assert result.get("success") is False


# ── WS Entity Registry ───────────────────────────────────

async def test_ws_entity_registry_update_name(rest, ws):
    """WS entity_registry/update sets friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_reg_{tag}"
    await rest.set_state(eid, "0")
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name=f"Updated Name {tag}",
    )
    assert result.get("success") is True
    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == f"Updated Name {tag}"


async def test_ws_entity_registry_update_icon(rest, ws):
    """WS entity_registry/update sets icon."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_icon_{tag}"
    await rest.set_state(eid, "0")
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        icon="mdi:thermometer",
    )
    assert result.get("success") is True
    state = await rest.get_state(eid)
    assert state["attributes"]["icon"] == "mdi:thermometer"


async def test_ws_entity_registry_update_area(rest, ws):
    """WS entity_registry/update assigns entity to area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"ws_ereg_area_{tag}"
    eid = f"sensor.ws_ereg_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name="Entity Area",
    )
    await rest.set_state(eid, "0")
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        area_id=aid,
    )
    assert result.get("success") is True


async def test_ws_entity_registry_update_nonexistent(ws):
    """WS entity_registry/update for nonexistent entity fails."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "config/entity_registry/update",
        entity_id=f"sensor.nonexist_{tag}",
        name="Nope",
    )
    assert result.get("success") is False


# ── WS Misc Commands ─────────────────────────────────────

async def test_ws_subscribe_trigger(ws):
    """WS subscribe_trigger succeeds."""
    result = await ws.send_command("subscribe_trigger")
    assert result.get("success") is True


async def test_ws_lovelace_config(ws):
    """WS lovelace/config returns stub with views and title."""
    result = await ws.send_command("lovelace/config")
    assert result.get("success") is True
    data = result.get("result", {})
    assert "views" in data
    assert data.get("title") == "Marge"


async def test_ws_unknown_command(ws):
    """Unknown WS command returns success=false."""
    result = await ws.send_command("totally_unknown_command")
    assert result.get("success") is False
