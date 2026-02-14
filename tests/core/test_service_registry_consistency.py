"""
CTS -- Service Registry Consistency Tests

Tests REST /api/services listing format, domain coverage,
service call fallback behavior (generic turn_on/turn_off/toggle),
and handler consistency across REST and WebSocket interfaces.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_services_list_is_array(rest):
    """GET /api/services returns JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_services_list_has_domains(rest):
    """Service listing includes core domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [entry["domain"] for entry in data]
    for expected in ["light", "switch", "lock", "climate", "cover", "fan"]:
        assert expected in domains, f"Missing domain: {expected}"


async def test_services_entry_has_services_map(rest):
    """Each service entry has domain and services map."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "domain" in entry
        assert "services" in entry
        assert isinstance(entry["services"], dict)


async def test_light_services_registered(rest):
    """Light domain has turn_on, turn_off, toggle services."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light_entry = next(e for e in data if e["domain"] == "light")
    services = list(light_entry["services"].keys())
    assert "turn_on" in services
    assert "turn_off" in services
    assert "toggle" in services


async def test_climate_services_registered(rest):
    """Climate domain has set_temperature, set_hvac_mode, etc."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    climate_entry = next(e for e in data if e["domain"] == "climate")
    services = list(climate_entry["services"].keys())
    assert "set_temperature" in services
    assert "set_hvac_mode" in services


async def test_service_entry_has_description(rest):
    """Each service has a description field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        for svc_name, svc_info in entry["services"].items():
            assert "description" in svc_info, f"Missing description for {entry['domain']}.{svc_name}"


async def test_fallback_turn_on_unknown_domain(rest):
    """Unknown domain with turn_on falls back to generic handler."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom_domain.fb_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("custom_domain", "turn_on", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_fallback_turn_off_unknown_domain(rest):
    """Unknown domain with turn_off falls back to generic handler."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom_domain.fboff_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("custom_domain", "turn_off", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_fallback_toggle_unknown_domain(rest):
    """Unknown domain with toggle falls back to generic handler."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom_domain.fbtog_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("custom_domain", "toggle", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_unknown_service_no_crash(rest):
    """Unknown service on unknown domain returns 200 (no crash)."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/fake_domain_{tag}/fake_service_{tag}",
        json={"entity_id": "sensor.doesnt_matter"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_service_call_empty_entity_list(rest):
    """Service call with no entity_id returns 200 with empty result."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_service_call_returns_changed_states(rest):
    """Service call returns the changed entity states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.svc_ret_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    # Response should contain the changed state(s)
    assert isinstance(data, (dict, list))


async def test_rest_and_ws_services_match(rest, ws):
    """REST /api/services and WS get_services return same domains."""
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    rest_domains = sorted(e["domain"] for e in rest_resp.json())

    ws_resp = await ws.send_command("get_services")
    ws_domains = sorted(e["domain"] for e in ws_resp["result"])

    assert rest_domains == ws_domains


async def test_services_sorted_by_domain(rest):
    """Service listing domains are in alphabetical order."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert domains == sorted(domains)
