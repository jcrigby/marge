"""
CTS -- Service Listing Depth Tests

Tests GET /api/services and WS get_services to verify all registered
domains and services appear correctly.
"""

import pytest

pytestmark = pytest.mark.asyncio

EXPECTED_DOMAINS = [
    "light", "switch", "lock", "climate", "cover", "fan",
    "media_player", "alarm_control_panel", "vacuum", "siren",
    "valve", "humidifier", "camera", "number", "select",
    "input_boolean", "input_number", "input_text", "input_select",
    "input_datetime", "timer", "counter", "button", "text",
    "automation", "scene", "homeassistant",
]


async def test_rest_services_has_all_domains(rest):
    """REST /api/services lists all expected domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    for d in EXPECTED_DOMAINS:
        assert d in domains, f"Missing domain: {d}"


async def test_ws_services_has_all_domains(ws):
    """WS get_services lists all expected domains."""
    resp = await ws.send_command("get_services")
    data = resp["result"]
    domains = [e["domain"] for e in data]
    for d in EXPECTED_DOMAINS:
        assert d in domains, f"Missing domain: {d}"


async def test_light_has_all_services(rest):
    """Light domain has turn_on, turn_off, toggle."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(e for e in data if e["domain"] == "light")
    for svc in ["turn_on", "turn_off", "toggle"]:
        assert svc in light["services"]


async def test_climate_has_set_services(rest):
    """Climate domain has set_temperature, set_hvac_mode, etc."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    climate = next(e for e in data if e["domain"] == "climate")
    for svc in ["set_temperature", "set_hvac_mode", "set_fan_mode", "turn_on", "turn_off"]:
        assert svc in climate["services"]


async def test_cover_has_position_service(rest):
    """Cover domain has set_cover_position."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    cover = next(e for e in data if e["domain"] == "cover")
    assert "set_cover_position" in cover["services"]


async def test_media_player_has_media_services(rest):
    """Media player has play, pause, stop, volume."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    mp = next(e for e in data if e["domain"] == "media_player")
    for svc in ["media_play", "media_pause", "media_stop", "volume_set"]:
        assert svc in mp["services"]


async def test_lock_has_open_service(rest):
    """Lock domain has lock, unlock, open."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    lock = next(e for e in data if e["domain"] == "lock")
    for svc in ["lock", "unlock", "open"]:
        assert svc in lock["services"]


async def test_services_sorted_alphabetically(rest):
    """Domains are sorted alphabetically."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert domains == sorted(domains)


async def test_service_entry_has_description(rest):
    """Service entries have description field (even if empty)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data[:5]:
        for svc_name, svc_info in entry["services"].items():
            assert "description" in svc_info
