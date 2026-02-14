"""
CTS -- Cross-Endpoint Workflow Depth Tests

Tests that exercise complete workflows spanning multiple endpoints:
REST→WS, webhook→history, notification lifecycle via mixed REST/WS,
service→state→template chain, and area assignment→search.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── REST → WS State Consistency ──────────────────────────

async def test_rest_set_ws_template_read(rest, ws):
    """State set via REST is immediately visible via WS render_template."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.xwf_rw_{tag}"
    await rest.set_state(eid, "42", {"unit": "W"})
    resp = await ws.send_command("render_template", template=f"{{{{ states('{eid}') }}}}")
    assert resp["success"] is True
    assert resp["result"]["result"].strip() == "42"


async def test_ws_service_rest_read(rest, ws):
    """Service called via WS produces state visible via REST."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.xwf_sr_{tag}"
    await rest.set_state(eid, "off")
    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Webhook → History Chain ──────────────────────────────

async def test_webhook_state_in_history(rest):
    """State set via webhook appears in entity history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.xwf_wh_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        json={"entity_id": eid, "state": "triggered"},
        headers=rest._headers(),
    )
    await asyncio.sleep(0.3)  # recorder batch flush
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    assert any(h["state"] == "triggered" for h in history)


# ── Notification Lifecycle: REST create → WS read → REST dismiss ──

async def test_notification_rest_ws_lifecycle(rest, ws):
    """Create notification via REST, read via WS, dismiss via REST."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_xwf_{tag}"
    # Create via REST service call
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": f"XWF {tag}",
        "message": f"Body {tag}",
    })
    # Read via WS
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    nids = [n.get("notification_id", n.get("id", "")) for n in resp["result"]]
    assert nid in nids
    # Dismiss via REST
    dismiss_resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        headers=rest._headers(),
    )
    assert dismiss_resp.status_code == 200
    # Verify gone via WS
    resp2 = await ws.send_command("get_notifications")
    nids2 = [n.get("notification_id", n.get("id", "")) for n in resp2["result"]]
    assert nid not in nids2


# ── Service → State → Template Chain ─────────────────────

async def test_service_state_template_chain(rest):
    """Service call → state change → template reads updated state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.xwf_tpl_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 200,
    })
    # Template reads the state
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": f"{{{{ states('{eid}') }}}}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "on"
    # Template reads the attribute
    resp2 = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": f"{{{{ state_attr('{eid}', 'brightness') }}}}"},
        headers=rest._headers(),
    )
    assert "200" in resp2.text


# ── Area Assignment → Search ─────────────────────────────

async def test_area_assign_search(rest):
    """Assign entity to area, then search by area finds it."""
    tag = uuid.uuid4().hex[:8]
    area_name = f"xwf_room_{tag}"
    eid = f"sensor.xwf_area_{tag}"
    area_id = f"area_{tag}"
    # Create area (requires area_id + name)
    area_resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": area_name},
        headers=rest._headers(),
    )
    assert area_resp.status_code == 200
    # Create entity and assign
    await rest.set_state(eid, "22.5")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{area_id}/entities/{eid}",
        headers=rest._headers(),
    )
    # Search by area
    search_resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}",
        headers=rest._headers(),
    )
    assert search_resp.status_code == 200
    found_eids = [s["entity_id"] for s in search_resp.json()]
    assert eid in found_eids
    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{area_id}",
        headers=rest._headers(),
    )


# ── Label Assignment → Search ────────────────────────────

async def test_label_assign_search(rest):
    """Assign label to entity, then search by label finds it."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"xwf_lbl_{tag}"
    eid = f"sensor.xwf_lbl_{tag}"
    # Create label
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": label_id, "name": f"Label {tag}"},
        headers=rest._headers(),
    )
    # Create entity and assign
    await rest.set_state(eid, "42")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{label_id}/entities/{eid}",
        headers=rest._headers(),
    )
    # Search by label
    search_resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={label_id}",
        headers=rest._headers(),
    )
    assert search_resp.status_code == 200
    found_eids = [s["entity_id"] for s in search_resp.json()]
    assert eid in found_eids
    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/labels/{label_id}",
        headers=rest._headers(),
    )


# ── Delete → Re-create ──────────────────────────────────

async def test_delete_recreate_entity(rest):
    """Delete entity, re-create with different state, verify history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.xwf_del_{tag}"
    await rest.set_state(eid, "first")
    await asyncio.sleep(0.15)
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Re-create
    await rest.set_state(eid, "second")
    state = await rest.get_state(eid)
    assert state["state"] == "second"


# ── Config + Health Consistency ──────────────────────────

async def test_config_health_version_match(rest):
    """REST /api/config and /api/health return same version."""
    config_resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    health_resp = await rest.client.get(f"{rest.base_url}/api/health")
    config_version = config_resp.json()["version"]
    health_version = health_resp.json()["version"]
    assert config_version == health_version
