"""
CTS -- Area/Label Cross-API Depth Tests

Tests that area and label operations via REST are reflected in
WS registry queries, and vice versa.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── REST Area → WS Registry ─────────────────────────────

async def test_rest_area_visible_in_ws(rest, ws):
    """Area created via REST appears in WS area_registry/list."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_xapi_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Cross {tag}"},
    )

    result = await ws.send_command("config/area_registry/list")
    area_ids = [a["area_id"] for a in result["result"]]
    assert aid in area_ids


async def test_ws_area_visible_in_rest(rest, ws):
    """Area created via WS appears in REST /api/areas."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_wsrest_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name=f"WS Area {tag}",
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    area_ids = [a["area_id"] for a in resp.json()]
    assert aid in area_ids


# ── REST Label → WS Registry ────────────────────────────

async def test_rest_label_visible_in_ws(rest, ws):
    """Label created via REST appears in WS label_registry/list."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_xapi_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": f"Cross {tag}", "color": ""},
    )

    result = await ws.send_command("config/label_registry/list")
    label_ids = [l["label_id"] for l in result["result"]]
    assert lid in label_ids


async def test_ws_label_visible_in_rest(rest, ws):
    """Label created via WS appears in REST /api/labels."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_wsrest_{tag}"
    await ws.send_command(
        "config/label_registry/create",
        label_id=lid,
        name=f"WS Label {tag}",
        color="#AABBCC",
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label_ids = [l["label_id"] for l in resp.json()]
    assert lid in label_ids


# ── Entity Assignment Cross-API ──────────────────────────

async def test_rest_area_assign_ws_verify(rest, ws):
    """Entity assigned to area via REST appears in WS entity_registry."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_asgnx_{tag}"
    eid = f"sensor.xapi_a_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": "Assign Room"},
    )
    await rest.set_state(eid, "1")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )

    # Verify via REST area entities
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids


async def test_rest_label_assign_ws_verify(rest, ws):
    """Entity labeled via REST appears in WS label listing."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_asgnx_{tag}"
    eid = f"sensor.xapi_l_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": "Cross Label", "color": ""},
    )
    await rest.set_state(eid, "1")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )

    # Verify via WS
    result = await ws.send_command("config/label_registry/list")
    label = next(l for l in result["result"] if l["label_id"] == lid)
    assert eid in label["entities"]


# ── Delete Cross-API ─────────────────────────────────────

async def test_rest_delete_area_ws_verify(rest, ws):
    """Area deleted via REST removed from WS area_registry."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_delx_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": "Del Room"},
    )
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{aid}",
        headers=rest._headers(),
    )

    result = await ws.send_command("config/area_registry/list")
    area_ids = [a["area_id"] for a in result["result"]]
    assert aid not in area_ids


async def test_ws_delete_area_rest_verify(rest, ws):
    """Area deleted via WS removed from REST /api/areas."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_wsdel_{tag}"
    await ws.send_command(
        "config/area_registry/create",
        area_id=aid,
        name="WS Del",
    )
    await ws.send_command(
        "config/area_registry/delete",
        area_id=aid,
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    area_ids = [a["area_id"] for a in resp.json()]
    assert aid not in area_ids
