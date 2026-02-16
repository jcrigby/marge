"""
CTS -- Area and Label Registry Lifecycle Tests

Tests complete CRUD lifecycle for areas and labels via REST API,
entity assignment/unassignment, and cross-reference queries.
"""

import pytest
import uuid

pytestmark = pytest.mark.asyncio


# ── Area Lifecycle ───────────────────────────────────────

async def test_area_create(rest):
    """Create area via REST POST."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"lc_area_{tag}", "name": f"LC Room {tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_area_list_includes_created(rest):
    """Created area appears in area list."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"lc_list_{tag}", "name": f"Listed {tag}"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    areas = resp.json()
    assert isinstance(areas, list)
    ids = [a["area_id"] for a in areas]
    assert f"lc_list_{tag}" in ids


async def test_area_delete(rest):
    """Delete area via REST DELETE."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"lc_del_{tag}", "name": f"Delete Me {tag}"},
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/lc_del_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_area_assign_entity(rest):
    """Assign entity to area."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"lc_asgn_{tag}", "name": f"Assign {tag}"},
        headers=rest._headers(),
    )
    await rest.set_state(f"sensor.lc_ent_{tag}", "50")
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/lc_asgn_{tag}/entities/sensor.lc_ent_{tag}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_area_list_entities(rest):
    """List entities in area."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"lc_le_{tag}", "name": f"ListEnt {tag}"},
        headers=rest._headers(),
    )
    await rest.set_state(f"sensor.lc_lent_{tag}", "50")
    await rest.client.post(
        f"{rest.base_url}/api/areas/lc_le_{tag}/entities/sensor.lc_lent_{tag}",
        json={},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/lc_le_{tag}/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entities = resp.json()
    assert isinstance(entities, list)


async def test_area_unassign_entity(rest):
    """Unassign entity from area."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"lc_un_{tag}", "name": f"Unassign {tag}"},
        headers=rest._headers(),
    )
    await rest.set_state(f"sensor.lc_unent_{tag}", "50")
    await rest.client.post(
        f"{rest.base_url}/api/areas/lc_un_{tag}/entities/sensor.lc_unent_{tag}",
        json={},
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/lc_un_{tag}/entities/sensor.lc_unent_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Label Lifecycle ──────────────────────────────────────

async def test_label_create(rest):
    """Create label via REST POST."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lc_lbl_{tag}", "name": f"Label {tag}", "color": "#ff0000"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_label_list_includes_created(rest):
    """Created label appears in label list."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lc_ll_{tag}", "name": f"Listed {tag}", "color": "#00ff00"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    labels = resp.json()
    assert isinstance(labels, list)
    ids = [l["label_id"] for l in labels]
    assert f"lc_ll_{tag}" in ids


async def test_label_delete(rest):
    """Delete label via REST DELETE."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lc_ld_{tag}", "name": f"Delete {tag}", "color": "#0000ff"},
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/lc_ld_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_label_assign_entity(rest):
    """Assign label to entity."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lc_la_{tag}", "name": f"Assign {tag}", "color": ""},
        headers=rest._headers(),
    )
    await rest.set_state(f"sensor.lc_lblent_{tag}", "50")
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/lc_la_{tag}/entities/sensor.lc_lblent_{tag}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_label_unassign_entity(rest):
    """Unassign label from entity."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lc_lu_{tag}", "name": f"Unassign {tag}", "color": ""},
        headers=rest._headers(),
    )
    await rest.set_state(f"sensor.lc_luent_{tag}", "50")
    await rest.client.post(
        f"{rest.base_url}/api/labels/lc_lu_{tag}/entities/sensor.lc_luent_{tag}",
        json={},
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/lc_lu_{tag}/entities/sensor.lc_luent_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Device Registry ──────────────────────────────────────

async def test_device_create(rest):
    """Create device via REST POST."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": f"lc_dev_{tag}",
            "name": f"Device {tag}",
            "manufacturer": "TestCo",
            "model": "T100",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_device_list(rest):
    """List devices via REST GET."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    devices = resp.json()
    assert isinstance(devices, list)


async def test_device_assign_entity(rest):
    """Assign entity to device."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"lc_da_{tag}", "name": f"Dev {tag}"},
        headers=rest._headers(),
    )
    await rest.set_state(f"sensor.lc_dent_{tag}", "50")
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/lc_da_{tag}/entities/sensor.lc_dent_{tag}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# -- from test_extended_api.py --

async def test_area_entity_listing_includes_state(rest):
    """GET /api/areas/:id/entities returns full entity state objects."""
    await rest.set_state("sensor.area_state_test", "55", {"unit_of_measurement": "W"})
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "cts_state_room", "name": "State Room"},
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas/cts_state_room/entities/sensor.area_state_test",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/cts_state_room/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entities = resp.json()
    found = next((e for e in entities if e.get("entity_id") == "sensor.area_state_test"), None)
    assert found is not None
    assert found["state"] == "55"

    # Cleanup
    await rest.client.delete(f"{rest.base_url}/api/areas/cts_state_room/entities/sensor.area_state_test",
                              headers=rest._headers())
    await rest.client.delete(f"{rest.base_url}/api/areas/cts_state_room", headers=rest._headers())


# -- from test_extended_api.py --

async def test_area_duplicate_entity_assignment(rest):
    """Assigning same entity to area twice is idempotent."""
    await rest.set_state("sensor.dup_area_test", "10")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "dup_test_room", "name": "Dup Room"},
    )

    # Assign twice
    for _ in range(2):
        resp = await rest.client.post(
            f"{rest.base_url}/api/areas/dup_test_room/entities/sensor.dup_area_test",
            headers=rest._headers(),
        )
        assert resp.status_code == 200

    # Verify entity appears only once
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    areas = resp.json()
    room = next((a for a in areas if a["area_id"] == "dup_test_room"), None)
    assert room is not None
    count = room["entities"].count("sensor.dup_area_test")
    assert count == 1

    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/areas/dup_test_room",
        headers=rest._headers(),
    )
