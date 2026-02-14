"""
CTS -- REST Services and Events Listing Depth Tests

Tests GET /api/services and GET /api/events endpoints: response
format, known domains present, service entries have domain/services
keys, events listing format, and fire_event endpoint.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── GET /api/services ────────────────────────────────────

async def test_services_returns_200(rest):
    """GET /api/services returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_services_returns_array(rest):
    """GET /api/services returns an array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_services_entry_has_domain(rest):
    """Each service entry has domain field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "domain" in entry


async def test_services_entry_has_services(rest):
    """Each service entry has services field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "services" in entry
        assert isinstance(entry["services"], dict)


async def test_services_contains_light(rest):
    """Services listing includes light domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    domains = [e["domain"] for e in resp.json()]
    assert "light" in domains


async def test_services_contains_switch(rest):
    """Services listing includes switch domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    domains = [e["domain"] for e in resp.json()]
    assert "switch" in domains


async def test_services_contains_climate(rest):
    """Services listing includes climate domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    domains = [e["domain"] for e in resp.json()]
    assert "climate" in domains


async def test_services_light_has_turn_on(rest):
    """Light domain has turn_on service."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    light = next(e for e in resp.json() if e["domain"] == "light")
    assert "turn_on" in light["services"]


async def test_services_light_has_turn_off(rest):
    """Light domain has turn_off service."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    light = next(e for e in resp.json() if e["domain"] == "light")
    assert "turn_off" in light["services"]


# ── GET /api/events ──────────────────────────────────────

async def test_events_returns_200(rest):
    """GET /api/events returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_events_returns_array(rest):
    """GET /api/events returns an array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_events_entry_has_event(rest):
    """Each event entry has event field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "event" in entry


async def test_events_entry_has_listener_count(rest):
    """Each event entry has listener_count field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "listener_count" in entry


# ── POST /api/events/{event_type} ────────────────────────

async def test_fire_event_returns_200(rest):
    """POST /api/events/test_event returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_event_{tag}",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 200


async def test_fire_event_returns_message(rest):
    """POST /api/events/test returns JSON with message."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/fired_{tag}",
        headers=rest._headers(),
        json={},
    )
    data = resp.json()
    assert "message" in data
