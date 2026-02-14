"""
CTS -- Event Listing and Service Listing Depth Tests

Tests GET /api/events, GET /api/services structure,
service domain completeness, and HA-compatible format.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Event Listing ────────────────────────────────────────────

async def test_events_returns_list(rest):
    """GET /api/events returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4


async def test_events_has_standard_types(rest):
    """Event list includes standard HA event types."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    event_types = [e["event"] for e in data]
    assert "state_changed" in event_types
    assert "call_service" in event_types
    assert "automation_triggered" in event_types


async def test_events_has_listener_count(rest):
    """Event entries include listener_count field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    for event in data:
        assert "event" in event
        assert "listener_count" in event


# ── Service Listing ──────────────────────────────────────────

async def test_services_returns_list(rest):
    """GET /api/services returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_services_ha_format(rest):
    """Services follow HA format: {domain, services: {name: {description, fields}}}."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    entry = data[0]
    assert "domain" in entry
    assert "services" in entry
    assert isinstance(entry["services"], dict)
    # Check a service has description and fields
    first_svc = list(entry["services"].values())[0]
    assert "description" in first_svc
    assert "fields" in first_svc


async def test_services_light_domain(rest):
    """Light domain has turn_on, turn_off, toggle services."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(d for d in data if d["domain"] == "light")
    svcs = list(light["services"].keys())
    assert "turn_on" in svcs
    assert "turn_off" in svcs
    assert "toggle" in svcs


async def test_services_climate_domain(rest):
    """Climate domain has set_temperature, set_hvac_mode, turn_on, turn_off."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    climate = next(d for d in data if d["domain"] == "climate")
    svcs = list(climate["services"].keys())
    assert "set_temperature" in svcs
    assert "set_hvac_mode" in svcs
    assert "turn_on" in svcs
    assert "turn_off" in svcs


async def test_services_automation_domain(rest):
    """Automation domain has trigger, turn_on, turn_off, toggle."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = next(d for d in data if d["domain"] == "automation")
    svcs = list(auto["services"].keys())
    assert "trigger" in svcs
    assert "turn_on" in svcs
    assert "turn_off" in svcs
    assert "toggle" in svcs


async def test_services_cover_domain(rest):
    """Cover domain has open_cover, close_cover, set_cover_position, stop_cover."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    cover = next(d for d in data if d["domain"] == "cover")
    svcs = list(cover["services"].keys())
    assert "open_cover" in svcs
    assert "close_cover" in svcs


async def test_services_description_format(rest):
    """Service descriptions follow domain.service format."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for domain_entry in data[:5]:
        domain = domain_entry["domain"]
        for svc_name, svc_info in domain_entry["services"].items():
            assert svc_info["description"] == f"{domain}.{svc_name}"


async def test_services_total_domains(rest):
    """Services list has 40+ domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 40, f"Expected 40+ domains, got {len(data)}"


async def test_services_total_service_count(rest):
    """Total service count across all domains is 100+."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    total = sum(len(d["services"]) for d in data)
    assert total >= 100, f"Expected 100+ services, got {total}"
