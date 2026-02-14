"""
CTS -- WS Entity Registry Update, Lovelace, and Misc Command Depth Tests

Tests WebSocket config/entity_registry/update (name, icon, area assignment),
lovelace/config stub, subscribe_trigger, unsubscribe_events, and unknown
command handling.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Entity Registry Update ──────────────────────────────

async def test_entity_registry_update_name(rest, ws):
    """config/entity_registry/update sets friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.reg_name_{tag}"
    await rest.set_state(eid, "42")
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name=f"Updated {tag}",
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == f"Updated {tag}"


async def test_entity_registry_update_icon(rest, ws):
    """config/entity_registry/update sets icon attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.reg_icon_{tag}"
    await rest.set_state(eid, "50")
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        icon="mdi:thermometer",
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"]["icon"] == "mdi:thermometer"


async def test_entity_registry_update_preserves_state(rest, ws):
    """config/entity_registry/update doesn't change entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.reg_pres_{tag}"
    await rest.set_state(eid, "99")
    await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name="Preserved",
    )
    state = await rest.get_state(eid)
    assert state["state"] == "99"


async def test_entity_registry_update_nonexistent_fails(ws):
    """config/entity_registry/update on non-existent entity returns failure."""
    resp = await ws.send_command(
        "config/entity_registry/update",
        entity_id="sensor.nonexistent_xyz_99",
        name="Nope",
    )
    assert resp["success"] is False


async def test_entity_registry_update_name_and_icon(rest, ws):
    """config/entity_registry/update can set both name and icon at once."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.reg_both_{tag}"
    await rest.set_state(eid, "10")
    await ws.send_command(
        "config/entity_registry/update",
        entity_id=eid,
        name=f"Both {tag}",
        icon="mdi:lightbulb",
    )
    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == f"Both {tag}"
    assert state["attributes"]["icon"] == "mdi:lightbulb"


# ── Lovelace Config ─────────────────────────────────────

async def test_lovelace_config_returns_stub(ws):
    """lovelace/config returns a minimal config with views and title."""
    resp = await ws.send_command("lovelace/config")
    assert resp["success"] is True
    config = resp["result"]
    assert "views" in config
    assert isinstance(config["views"], list)
    assert config["title"] == "Marge"


# ── Subscribe/Unsubscribe ───────────────────────────────

async def test_subscribe_trigger(ws):
    """subscribe_trigger returns success."""
    resp = await ws.send_command("subscribe_trigger")
    assert resp["success"] is True


async def test_unsubscribe_events(ws):
    """unsubscribe_events returns success."""
    # First subscribe to get a subscription ID
    sub_id = await ws.subscribe_events()
    resp = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert resp["success"] is True


# ── Unknown Command ─────────────────────────────────────

async def test_unknown_command_returns_failure(ws):
    """Unknown WS command returns success=false."""
    resp = await ws.send_command("totally_unknown_command_xyz")
    assert resp["success"] is False


# ── Entity Registry List ────────────────────────────────

async def test_entity_registry_list(rest, ws):
    """config/entity_registry/list returns entity entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rl_{tag}"
    await rest.set_state(eid, "1")
    resp = await ws.send_command("config/entity_registry/list")
    assert resp["success"] is True
    entries = resp["result"]
    assert isinstance(entries, list)
    assert any(e["entity_id"] == eid for e in entries)


async def test_entity_registry_list_has_platform(rest, ws):
    """config/entity_registry/list entries have platform field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rlp_{tag}"
    await rest.set_state(eid, "2")
    resp = await ws.send_command("config/entity_registry/list")
    entries = resp["result"]
    entry = next((e for e in entries if e["entity_id"] == eid), None)
    assert entry is not None
    assert entry["platform"] == "mqtt"
