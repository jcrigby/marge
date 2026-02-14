"""
CTS -- REST Device Entity Assignment Depth Tests

Tests device registry: create device, assign entity to device,
list devices, and delete device.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Create Device ───────────────────────────────────────

async def test_create_device(rest):
    """POST /api/devices creates device."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": f"dev_{tag}", "name": f"Device {tag}"},
    )
    assert resp.status_code == 200


async def test_created_device_in_listing(rest):
    """Created device appears in GET /api/devices."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_list_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": f"Dev {tag}"},
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    dids = [d["device_id"] for d in resp.json()]
    assert did in dids


# ── Assign Entity to Device ────────────────────────────

async def test_assign_entity_to_device(rest):
    """POST assigns entity to device."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_asgn_{tag}"
    eid = f"sensor.dasgn_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": f"Dev {tag}"},
    )
    await rest.set_state(eid, "1")
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/{did}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Delete Device ───────────────────────────────────────

async def test_delete_device(rest):
    """DELETE /api/devices/<did> removes device."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": did, "name": f"Del Dev {tag}"},
    )
    del_resp = await rest.client.delete(
        f"{rest.base_url}/api/devices/{did}",
        headers=rest._headers(),
    )
    assert del_resp.status_code == 200

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    dids = [d["device_id"] for d in resp.json()]
    assert did not in dids


# ── List Devices ────────────────────────────────────────

async def test_list_devices_returns_200(rest):
    """GET /api/devices returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_list_devices_returns_array(rest):
    """GET /api/devices returns JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert isinstance(resp.json(), list)
