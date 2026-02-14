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
