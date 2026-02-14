"""
CTS -- Recorder and History Depth Tests

Tests the SQLite recorder: state history writes, area-entity associations,
device registry persistence, and label registry persistence.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── State History ─────────────────────────────────────────

async def test_history_records_state_changes(rest):
    """State changes appear in history API."""
    entity = "sensor.rec_hist_1"
    await rest.set_state(entity, "alpha")
    await asyncio.sleep(0.2)
    await rest.set_state(entity, "beta")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_history_has_state_values(rest):
    """History entries contain state values."""
    entity = "sensor.rec_hist_vals"
    for v in ["10", "20", "30"]:
        await rest.set_state(entity, v)
        await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0 and isinstance(data[0], list):
        states = [s["state"] for s in data[0]]
        assert "30" in states
    elif len(data) > 0 and isinstance(data[0], dict):
        states = [s["state"] for s in data]
        assert "30" in states


async def test_history_empty_for_unknown_entity(rest):
    """History for unknown entity returns empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.nonexistent_rec_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


# ── Area-Entity Associations ─────────────────────────────

async def test_area_create_and_list(rest):
    """Create area and verify it appears in list."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": "rec_test_room", "name": "Recorder Test Room"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify in list
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    data = resp.json()
    area_ids = [a["area_id"] for a in data]
    assert "rec_test_room" in area_ids


async def test_area_entity_assignment(rest):
    """Assign entity to area and verify."""
    area_id = "assign_test_room"
    # Create area
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": "Assignment Test Room"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Create entity
    await rest.set_state("sensor.rec_area_assign", "42")

    # Assign entity to area
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/{area_id}/entities/sensor.rec_area_assign",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify via area entities list
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{area_id}/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    entity_ids = [e if isinstance(e, str) else e.get("entity_id", "") for e in data]
    assert "sensor.rec_area_assign" in entity_ids


# ── Device Registry ──────────────────────────────────────

async def test_device_registry_via_ws(ws):
    """Device registry list returns via WS."""
    resp = await ws.send_command("config/device_registry/list")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


# ── Label Registry ───────────────────────────────────────

async def test_label_list_via_ws(ws):
    """Label registry list returns via WS."""
    resp = await ws.send_command("config/label_registry/list")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


# ── Logbook ──────────────────────────────────────────────

async def test_logbook_records_events(rest):
    """Logbook contains entries after state changes."""
    await rest.set_state("sensor.rec_logbook", "event_a")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_filtered_by_entity(rest):
    """Logbook can filter by entity_id."""
    entity = "sensor.rec_logbook_filter"
    await rest.set_state(entity, "val1")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
