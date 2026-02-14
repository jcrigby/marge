"""
CTS -- Device Registry CRUD Depth Tests

Tests the device registry REST API: create devices, list devices,
delete devices, assign entities to devices, and verify device fields.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Device CRUD ───────────────────────────────────────────

async def test_create_device(rest):
    """POST /api/devices creates a device."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": f"dev_{tag}",
            "name": f"Test Device {tag}",
            "manufacturer": "TestCo",
            "model": "T-100",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"


async def test_list_devices(rest):
    """GET /api/devices returns a list containing created device."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_list_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": f"List {tag}"},
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    devices = resp.json()
    assert isinstance(devices, list)
    dids = [d["device_id"] for d in devices]
    assert did in dids


async def test_device_has_fields(rest):
    """Device object has name, manufacturer, model fields."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_fields_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": did,
            "name": f"Fields {tag}",
            "manufacturer": "Acme",
            "model": "Gadget",
        },
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    device = next(d for d in resp.json() if d["device_id"] == did)
    assert device["name"] == f"Fields {tag}"
    assert device["manufacturer"] == "Acme"
    assert device["model"] == "Gadget"


async def test_delete_device(rest):
    """DELETE /api/devices/{device_id} removes the device."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": "To Delete"},
    )
    resp = await rest.client.delete(
        f"{rest.base_url}/api/devices/{did}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    devices_resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    dids = [d["device_id"] for d in devices_resp.json()]
    assert did not in dids


# ── Device Entity Assignment ──────────────────────────────

async def test_assign_entity_to_device(rest):
    """POST /api/devices/{device_id}/entities/{entity_id} assigns entity."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_ent_{tag}"
    eid = f"sensor.dev_ent_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": "Entity Test"},
    )
    await rest.set_state(eid, "42")
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/{did}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_device_entity_count(rest):
    """Device listing shows entity_count after assignment."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_cnt_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": "Count"},
    )
    for i in range(2):
        eid = f"sensor.dc{i}_{tag}"
        await rest.set_state(eid, str(i))
        await rest.client.post(
            f"{rest.base_url}/api/devices/{did}/entities/{eid}",
            headers=rest._headers(),
        )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    device = next(d for d in resp.json() if d["device_id"] == did)
    assert device["entity_count"] == 2


async def test_device_entities_listed(rest):
    """Device listing includes entity IDs in entities array."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_ents_{tag}"
    eid = f"sensor.de_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": "Ents"},
    )
    await rest.set_state(eid, "1")
    await rest.client.post(
        f"{rest.base_url}/api/devices/{did}/entities/{eid}",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    device = next(d for d in resp.json() if d["device_id"] == did)
    assert eid in device["entities"]
