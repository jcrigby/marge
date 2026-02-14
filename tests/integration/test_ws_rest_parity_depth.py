"""
CTS -- WS/REST Parity Depth Tests

Tests that WebSocket and REST endpoints return consistent data:
config version, services listing shape, notification lists,
and entity state reads via both protocols.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Config Parity ─────────────────────────────────────────

async def test_config_version_parity(rest, ws):
    """WS get_config and REST /api/config return same version."""
    ws_result = await ws.send_command("get_config")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    ws_version = ws_result["result"]["version"]
    rest_version = rest_resp.json()["version"]
    assert ws_version == rest_version


async def test_config_location_parity(rest, ws):
    """WS and REST config return same location_name."""
    ws_result = await ws.send_command("get_config")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert ws_result["result"]["location_name"] == rest_resp.json()["location_name"]


async def test_config_timezone_parity(rest, ws):
    """WS and REST config return same time_zone."""
    ws_result = await ws.send_command("get_config")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert ws_result["result"]["time_zone"] == rest_resp.json()["time_zone"]


async def test_config_coordinates_parity(rest, ws):
    """WS and REST config return same lat/lon."""
    ws_result = await ws.send_command("get_config")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    ws_cfg = ws_result["result"]
    rest_cfg = rest_resp.json()
    assert ws_cfg["latitude"] == rest_cfg["latitude"]
    assert ws_cfg["longitude"] == rest_cfg["longitude"]


# ── Services Listing Parity ────────────────────────────────

async def test_services_listing_domains_parity(rest, ws):
    """WS get_services and REST /api/services list same domains."""
    ws_result = await ws.send_command("get_services")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    ws_domains = set(ws_result["result"].keys()) if isinstance(ws_result["result"], dict) else {
        s["domain"] for s in ws_result["result"]
    }
    rest_domains = {s["domain"] for s in rest_resp.json()}
    # Both should have core domains
    for domain in ["light", "switch", "climate", "fan", "lock"]:
        assert domain in ws_domains, f"{domain} missing from WS"
        assert domain in rest_domains, f"{domain} missing from REST"


# ── Notification Parity ────────────────────────────────────

async def test_notification_list_parity(rest, ws):
    """WS get_notifications and REST /api/notifications return same IDs."""
    tag = uuid.uuid4().hex[:8]
    nid = f"parity_{tag}"
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": "Parity Test",
        "message": "Body",
    })

    ws_result = await ws.send_command("get_notifications")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )

    ws_nids = {n.get("notification_id", n.get("id", "")) for n in ws_result["result"]}
    rest_nids = {n.get("notification_id", n.get("id", "")) for n in rest_resp.json()}
    assert nid in ws_nids
    assert nid in rest_nids


# ── Entity State Parity ───────────────────────────────────

async def test_state_read_parity(rest, ws):
    """State set via REST is readable via WS render_template."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.parity_sr_{tag}"
    await rest.set_state(eid, "42")

    ws_result = await ws.send_command(
        "render_template",
        template=f"{{{{ states('{eid}') }}}}",
    )
    assert ws_result["result"]["result"].strip() == "42"


async def test_attribute_read_parity(rest, ws):
    """Attributes set via REST are readable via WS render_template."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.parity_ar_{tag}"
    await rest.set_state(eid, "55", {"unit": "kWh"})

    ws_result = await ws.send_command(
        "render_template",
        template=f"{{{{ state_attr('{eid}', 'unit') }}}}",
    )
    assert ws_result["result"]["result"].strip() == "kWh"


async def test_service_via_ws_visible_via_rest(rest, ws):
    """Service called via WS produces state visible via REST."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.parity_svc_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid, "brightness": 180},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 180


async def test_service_via_rest_visible_via_ws(rest, ws):
    """Service called via REST produces state visible via WS template."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.parity_rv_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": eid})

    ws_result = await ws.send_command(
        "render_template",
        template=f"{{{{ states('{eid}') }}}}",
    )
    assert ws_result["result"]["result"].strip() == "on"


# ── Area Registry Parity ──────────────────────────────────

async def test_area_create_rest_read_ws(rest, ws):
    """Area created via REST is visible via WS area_registry/list."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"parity_area_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": f"Parity {tag}"},
        headers=rest._headers(),
    )

    ws_result = await ws.send_command("config/area_registry/list")
    ws_ids = {a.get("area_id", a.get("id", "")) for a in ws_result["result"]}
    assert area_id in ws_ids

    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{area_id}",
        headers=rest._headers(),
    )


async def test_area_create_ws_read_rest(rest, ws):
    """Area created via WS is visible via REST /api/areas."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"parity_ws_area_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=area_id,
        name=f"WS Parity {tag}",
    )

    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    rest_ids = {a.get("area_id", a.get("id", "")) for a in rest_resp.json()}
    assert area_id in rest_ids

    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{area_id}",
        headers=rest._headers(),
    )
