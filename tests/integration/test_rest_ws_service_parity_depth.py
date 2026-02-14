"""
CTS -- REST/WS Service Parity Depth Tests

Tests that the same service calls via REST and WS produce
identical state changes, verifying API consistency.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Switch Parity ───────────────────────────────────────

async def test_rest_switch_on_matches_ws(rest, ws):
    """switch.turn_on via REST produces same result as WS."""
    tag = uuid.uuid4().hex[:8]
    eid_r = f"switch.rswp_rest_{tag}"
    eid_w = f"switch.rswp_ws_{tag}"
    await rest.set_state(eid_r, "off")
    await rest.set_state(eid_w, "off")

    await rest.call_service("switch", "turn_on", {"entity_id": eid_r})
    await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid_w},
    )

    r_state = await rest.get_state(eid_r)
    w_state = await rest.get_state(eid_w)
    assert r_state["state"] == w_state["state"] == "on"


# ── Light Parity ────────────────────────────────────────

async def test_rest_light_brightness_matches_ws(rest, ws):
    """light.turn_on with brightness via REST matches WS."""
    tag = uuid.uuid4().hex[:8]
    eid_r = f"light.rswp_lrest_{tag}"
    eid_w = f"light.rswp_lws_{tag}"
    await rest.set_state(eid_r, "off")
    await rest.set_state(eid_w, "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": eid_r, "brightness": 128,
    })
    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid_w, "brightness": 128},
    )

    r_state = await rest.get_state(eid_r)
    w_state = await rest.get_state(eid_w)
    assert r_state["state"] == w_state["state"] == "on"
    assert r_state["attributes"]["brightness"] == w_state["attributes"]["brightness"] == 128


# ── Climate Parity ──────────────────────────────────────

async def test_rest_climate_temp_matches_ws(rest, ws):
    """climate.set_temperature via REST matches WS."""
    tag = uuid.uuid4().hex[:8]
    eid_r = f"climate.rswp_crest_{tag}"
    eid_w = f"climate.rswp_cws_{tag}"
    await rest.set_state(eid_r, "heat")
    await rest.set_state(eid_w, "heat")

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid_r, "temperature": 72,
    })
    await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        service_data={"entity_id": eid_w, "temperature": 72},
    )

    r_state = await rest.get_state(eid_r)
    w_state = await rest.get_state(eid_w)
    assert r_state["attributes"]["temperature"] == w_state["attributes"]["temperature"] == 72


# ── Cover Parity ────────────────────────────────────────

async def test_rest_cover_position_matches_ws(rest, ws):
    """cover.set_cover_position via REST matches WS."""
    tag = uuid.uuid4().hex[:8]
    eid_r = f"cover.rswp_cvrest_{tag}"
    eid_w = f"cover.rswp_cvws_{tag}"
    await rest.set_state(eid_r, "closed")
    await rest.set_state(eid_w, "closed")

    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid_r, "position": 50,
    })
    await ws.send_command(
        "call_service",
        domain="cover",
        service="set_cover_position",
        service_data={"entity_id": eid_w, "position": 50},
    )

    r_state = await rest.get_state(eid_r)
    w_state = await rest.get_state(eid_w)
    assert r_state["state"] == w_state["state"] == "open"
    assert r_state["attributes"]["current_position"] == w_state["attributes"]["current_position"] == 50


# ── Lock Parity ─────────────────────────────────────────

async def test_rest_lock_matches_ws(rest, ws):
    """lock.lock via REST matches WS."""
    tag = uuid.uuid4().hex[:8]
    eid_r = f"lock.rswp_lkrest_{tag}"
    eid_w = f"lock.rswp_lkws_{tag}"
    await rest.set_state(eid_r, "unlocked")
    await rest.set_state(eid_w, "unlocked")

    await rest.call_service("lock", "lock", {"entity_id": eid_r})
    await ws.send_command(
        "call_service",
        domain="lock",
        service="lock",
        service_data={"entity_id": eid_w},
    )

    r_state = await rest.get_state(eid_r)
    w_state = await rest.get_state(eid_w)
    assert r_state["state"] == w_state["state"] == "locked"


# ── Fan Parity ──────────────────────────────────────────

async def test_rest_fan_percentage_matches_ws(rest, ws):
    """fan.set_percentage via REST matches WS."""
    tag = uuid.uuid4().hex[:8]
    eid_r = f"fan.rswp_frest_{tag}"
    eid_w = f"fan.rswp_fws_{tag}"
    await rest.set_state(eid_r, "off")
    await rest.set_state(eid_w, "off")

    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid_r, "percentage": 75,
    })
    await ws.send_command(
        "call_service",
        domain="fan",
        service="set_percentage",
        service_data={"entity_id": eid_w, "percentage": 75},
    )

    r_state = await rest.get_state(eid_r)
    w_state = await rest.get_state(eid_w)
    assert r_state["state"] == w_state["state"] == "on"
    assert r_state["attributes"]["percentage"] == w_state["attributes"]["percentage"] == 75
