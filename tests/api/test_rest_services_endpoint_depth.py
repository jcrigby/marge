"""
CTS -- REST Services Endpoint Depth Tests

Tests GET /api/services (REST, not WS), POST /api/services/{domain}/{service}
response format, GET /api/events listing, and service call response body.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── GET /api/services ───────────────────────────────────

async def test_rest_services_returns_list(rest):
    """GET /api/services returns a list of domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_rest_services_has_domains(rest):
    """GET /api/services includes expected domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [s["domain"] for s in data]
    assert "light" in domains
    assert "switch" in domains
    assert "climate" in domains


async def test_rest_services_domain_has_services(rest):
    """Each domain in /api/services has services object."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "domain" in entry
        assert "services" in entry


# ── GET /api/events ─────────────────────────────────────

async def test_rest_events_returns_list(rest):
    """GET /api/events returns a list of event types."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_rest_events_has_state_changed(rest):
    """GET /api/events includes state_changed event type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    event_types = [e.get("event", "") for e in data]
    assert "state_changed" in event_types


# ── POST /api/services response ────────────────────────

async def test_service_call_returns_changed_states(rest):
    """POST /api/services/{domain}/{service} returns changed_states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_resp_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    changed = data["changed_states"]
    assert isinstance(changed, list)
    assert len(changed) >= 1
    assert changed[0]["entity_id"] == eid
    assert changed[0]["state"] == "on"


async def test_service_response_has_timestamps(rest):
    """Service call response includes timestamps."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.svc_ts_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    changed = resp.json()["changed_states"]
    assert "last_changed" in changed[0]
    assert "last_updated" in changed[0]


async def test_service_response_has_context(rest):
    """Service call response includes context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_ctx_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    changed = resp.json()["changed_states"]
    assert "context" in changed[0]
    assert "id" in changed[0]["context"]


# ── POST /api/fire_event ───────────────────────────────

async def test_rest_fire_event(rest):
    """POST /api/events/{event_type} fires event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_event_{tag}",
        json={"data": "test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── POST /api/template ─────────────────────────────────

async def test_rest_render_template(rest):
    """POST /api/template renders a Jinja2 template."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_rest_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('" + eid + "') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result = resp.text if hasattr(resp, 'text') else resp.json()
    assert "42" in str(result)


async def test_rest_render_template_error(rest):
    """POST /api/template with invalid template returns error."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ invalid syntax!!!"},
        headers=rest._headers(),
    )
    # Should either return 400 or 200 with error message
    assert resp.status_code in (200, 400, 422)
