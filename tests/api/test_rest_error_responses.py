"""
CTS -- REST API Error Response Tests

Tests error response patterns: 404 consistency, malformed JSON handling,
wrong HTTP methods, missing required fields, and content-type validation.
"""

import uuid
import pytest
import httpx

pytestmark = pytest.mark.asyncio

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def test_404_nonexistent_entity():
    """GET nonexistent entity returns 404."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/sensor.nonexist_xyz_999", headers=HEADERS)
        assert r.status_code == 404


async def test_nonexistent_api_route():
    """GET nonexistent API route returns 200 (SPA fallback) or 404."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/nonexistent_endpoint", headers=HEADERS)
        # With dashboard fallback_service, unknown routes may return 200
        assert r.status_code in (200, 404)


async def test_405_get_on_post_only():
    """GET on POST-only endpoint returns 405."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/services/light/turn_on", headers=HEADERS)
        assert r.status_code == 405


async def test_malformed_json_state_set():
    """POST /api/states with invalid JSON returns 4xx."""
    tag = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE}/api/states/sensor.bad_{tag}",
            content="not valid json",
            headers=HEADERS,
        )
        assert r.status_code in (400, 415, 422)


async def test_service_call_invalid_json():
    """POST /api/services with invalid JSON returns 4xx."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE}/api/services/light/turn_on",
            content="{broken json",
            headers=HEADERS,
        )
        assert r.status_code in (400, 415, 422)


async def test_template_missing_template_field():
    """POST /api/template without template field returns 4xx."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE}/api/template",
            json={"not_template": "value"},
            headers=HEADERS,
        )
        assert r.status_code in (400, 422)


async def test_event_fire_returns_200():
    """POST /api/events/:type returns 200."""
    tag = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE}/api/events/test_event_{tag}",
            json={"key": "value"},
            headers=HEADERS,
        )
        assert r.status_code == 200


async def test_service_unknown_domain():
    """POST /api/services/fakeDomain/fakeService returns 200."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE}/api/services/fake_domain/fake_service",
            json={"entity_id": "fake.entity"},
            headers=HEADERS,
        )
        # Marge returns 200 even for unknown domains (HA-compatible)
        assert r.status_code == 200


async def test_delete_nonexistent_entity():
    """DELETE nonexistent entity returns 404."""
    async with httpx.AsyncClient() as c:
        r = await c.delete(
            f"{BASE}/api/states/sensor.definitely_missing_999",
            headers=HEADERS,
        )
        assert r.status_code == 404


async def test_get_health_format():
    """GET /api/health returns JSON with status field."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/health", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data


async def test_api_root_returns_message():
    """GET /api/ returns JSON with message."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "message" in data


async def test_state_set_returns_entity_format():
    """POST /api/states returns full entity JSON."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmt_{tag}"
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE}/api/states/{eid}",
            json={"state": "value", "attributes": {"unit": "test"}},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["entity_id"] == eid
        assert data["state"] == "value"
        assert "last_changed" in data
        assert "last_updated" in data
        assert "context" in data
        assert "attributes" in data


async def test_service_call_returns_json():
    """POST /api/services returns JSON response."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.resp_{tag}"
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{BASE}/api/states/{eid}",
            json={"state": "off"},
            headers=HEADERS,
        )
        r = await c.post(
            f"{BASE}/api/services/light/turn_on",
            json={"entity_id": eid},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (dict, list))
