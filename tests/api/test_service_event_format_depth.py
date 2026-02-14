"""
CTS -- Service List and Event List Format Depth Tests

Tests GET /api/services format (HA-compatible domain/services structure),
GET /api/events format (event types with listener counts), and
validates specific domain/service presence.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── GET /api/services ──────────────────────────────────────

async def test_services_returns_200(rest):
    """GET /api/services returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_services_returns_list(rest):
    """GET /api/services returns a JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_services_has_domain_field(rest):
    """Service entries have 'domain' field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "domain" in entry, f"Missing domain in {entry}"


async def test_services_has_services_dict(rest):
    """Service entries have 'services' dict field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "services" in entry
        assert isinstance(entry["services"], dict)


async def test_services_light_domain_present(rest):
    """Service list includes 'light' domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert "light" in domains


async def test_services_light_has_turn_on(rest):
    """Light domain includes turn_on service."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(e for e in data if e["domain"] == "light")
    assert "turn_on" in light["services"]


async def test_services_light_has_turn_off(rest):
    """Light domain includes turn_off service."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(e for e in data if e["domain"] == "light")
    assert "turn_off" in light["services"]


async def test_services_light_has_toggle(rest):
    """Light domain includes toggle service."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(e for e in data if e["domain"] == "light")
    assert "toggle" in light["services"]


async def test_services_switch_domain_present(rest):
    """Service list includes 'switch' domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert "switch" in domains


async def test_services_climate_domain_present(rest):
    """Service list includes 'climate' domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert "climate" in domains


async def test_services_lock_domain_present(rest):
    """Service list includes 'lock' domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert "lock" in domains


async def test_services_service_has_description(rest):
    """Service entries have description field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(e for e in data if e["domain"] == "light")
    turn_on = light["services"]["turn_on"]
    assert "description" in turn_on


# ── GET /api/events ────────────────────────────────────────

async def test_events_returns_200(rest):
    """GET /api/events returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_events_returns_list(rest):
    """GET /api/events returns a JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_events_has_event_field(rest):
    """Event entries have 'event' field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "event" in entry


async def test_events_has_listener_count(rest):
    """Event entries have 'listener_count' field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "listener_count" in entry


async def test_events_includes_state_changed(rest):
    """Event list includes 'state_changed' event type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    events = [e["event"] for e in data]
    assert "state_changed" in events


async def test_events_includes_call_service(rest):
    """Event list includes 'call_service' event type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    events = [e["event"] for e in data]
    assert "call_service" in events


async def test_events_includes_automation_triggered(rest):
    """Event list includes 'automation_triggered' event type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    events = [e["event"] for e in data]
    assert "automation_triggered" in events
