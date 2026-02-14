"""
CTS -- REST Device Listing Depth Tests

Tests GET /api/devices endpoint: response format, device fields,
and device creation via POST.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Device Listing ───────────────────────────────────────

async def test_devices_returns_200(rest):
    """GET /api/devices returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_devices_returns_array(rest):
    """GET /api/devices returns an array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert isinstance(resp.json(), list)


# ── Device Creation ──────────────────────────────────────

async def test_create_device(rest):
    """POST /api/devices creates device."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": f"dev_{tag}",
            "name": f"Test Device {tag}",
            "manufacturer": "ACME",
            "model": "Widget v1",
        },
    )
    assert resp.status_code == 200


async def test_created_device_in_listing(rest):
    """Created device appears in GET /api/devices."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_list_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": did,
            "name": f"Listed {tag}",
            "manufacturer": "Marge",
            "model": "Alpha",
        },
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    device_ids = [d["device_id"] for d in resp.json()]
    assert did in device_ids


async def test_device_has_name(rest):
    """Device entry has name field."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_name_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": did,
            "name": f"Named {tag}",
            "manufacturer": "X",
            "model": "Y",
        },
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    dev = next(d for d in resp.json() if d["device_id"] == did)
    assert dev["name"] == f"Named {tag}"


async def test_device_has_manufacturer(rest):
    """Device entry has manufacturer field."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_mfr_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": did,
            "name": "M",
            "manufacturer": "Zigbee Corp",
            "model": "Z1",
        },
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    dev = next(d for d in resp.json() if d["device_id"] == did)
    assert dev["manufacturer"] == "Zigbee Corp"


async def test_device_has_model(rest):
    """Device entry has model field."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_mdl_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": did,
            "name": "M",
            "manufacturer": "Co",
            "model": "Sensor Pro",
        },
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    dev = next(d for d in resp.json() if d["device_id"] == did)
    assert dev["model"] == "Sensor Pro"
