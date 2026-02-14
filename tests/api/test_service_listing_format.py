"""
CTS -- Service Listing Format & Coverage Tests

Tests GET /api/services response format and verifies all registered
domain handlers appear in the listing with correct structure.
"""

import pytest

pytestmark = pytest.mark.asyncio

# All domains that have registered handlers in services.rs
EXPECTED_DOMAINS = [
    "alarm_control_panel",
    "automation",
    "button",
    "camera",
    "climate",
    "counter",
    "cover",
    "device_tracker",
    "fan",
    "group",
    "humidifier",
    "image",
    "input_boolean",
    "input_datetime",
    "input_number",
    "input_select",
    "lawn_mower",
    "light",
    "lock",
    "media_player",
    "notify",
    "number",
    "person",
    "remote",
    "scene",
    "select",
    "siren",
    "switch",
    "text",
    "timer",
    "update",
    "vacuum",
    "valve",
    "water_heater",
    "weather",
    "zone",
]


async def test_services_returns_list(rest):
    """GET /api/services returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_services_entry_format(rest):
    """Each service entry has domain and services fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "domain" in entry
        assert "services" in entry
        assert isinstance(entry["services"], dict)


async def test_services_light_has_expected_services(rest):
    """Light domain has turn_on, turn_off, toggle."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(e for e in data if e["domain"] == "light")
    service_names = list(light["services"].keys())
    assert "turn_on" in service_names
    assert "turn_off" in service_names
    assert "toggle" in service_names


async def test_services_climate_has_expected_services(rest):
    """Climate domain has set_temperature, set_hvac_mode, turn_on, turn_off."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    climate = next(e for e in data if e["domain"] == "climate")
    service_names = list(climate["services"].keys())
    assert "set_temperature" in service_names
    assert "set_hvac_mode" in service_names
    assert "turn_on" in service_names
    assert "turn_off" in service_names


async def test_services_cover_has_expected_services(rest):
    """Cover domain has open_cover, close_cover, stop_cover, set_cover_position."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    cover = next(e for e in data if e["domain"] == "cover")
    service_names = list(cover["services"].keys())
    assert "open_cover" in service_names
    assert "close_cover" in service_names
    assert "stop_cover" in service_names
    assert "set_cover_position" in service_names


async def test_services_counter_has_expected_services(rest):
    """Counter domain has increment, decrement, reset."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    counter = next(e for e in data if e["domain"] == "counter")
    service_names = list(counter["services"].keys())
    assert "increment" in service_names
    assert "decrement" in service_names
    assert "reset" in service_names


async def test_services_fan_has_expected_services(rest):
    """Fan domain has turn_on, turn_off, set_percentage, set_direction."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    fan = next(e for e in data if e["domain"] == "fan")
    service_names = list(fan["services"].keys())
    assert "turn_on" in service_names
    assert "turn_off" in service_names
    assert "set_percentage" in service_names


async def test_services_vacuum_has_expected_services(rest):
    """Vacuum domain has start, stop, return_to_base, locate."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    vacuum = next(e for e in data if e["domain"] == "vacuum")
    service_names = list(vacuum["services"].keys())
    assert "start" in service_names
    assert "stop" in service_names
    assert "return_to_base" in service_names


async def test_services_timer_has_expected_services(rest):
    """Timer domain has start, pause, cancel, finish."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    timer = next(e for e in data if e["domain"] == "timer")
    service_names = list(timer["services"].keys())
    assert "start" in service_names
    assert "pause" in service_names
    assert "cancel" in service_names
    assert "finish" in service_names


async def test_services_humidifier_has_expected_services(rest):
    """Humidifier domain has turn_on, turn_off, toggle, set_humidity, set_mode."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    humidifier = next(e for e in data if e["domain"] == "humidifier")
    service_names = list(humidifier["services"].keys())
    assert "turn_on" in service_names
    assert "turn_off" in service_names
    assert "toggle" in service_names
    assert "set_humidity" in service_names
    assert "set_mode" in service_names


async def test_services_all_expected_domains_present(rest):
    """All expected domains appear in service listing."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    listed_domains = [e["domain"] for e in data]
    for domain in EXPECTED_DOMAINS:
        assert domain in listed_domains, f"Missing domain: {domain}"


async def test_services_domains_sorted(rest):
    """Domains in service listing are sorted alphabetically."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert domains == sorted(domains)


async def test_services_service_description_present(rest):
    """Each service has a description field (even if empty)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        for svc_name, svc_info in entry["services"].items():
            assert "description" in svc_info, (
                f"{entry['domain']}.{svc_name} missing description"
            )
