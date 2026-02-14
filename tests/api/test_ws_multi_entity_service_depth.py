"""
CTS -- WS Multi-Entity Service Call Depth Tests

Tests WebSocket call_service with multiple entity targets:
entity_id as array in service_data, entity_id in target,
and mixed scenarios.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Array Entity IDs in service_data ────────────────────

async def test_ws_service_array_entity_ids(rest, ws):
    """WS call_service with entity_id array affects all entities."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.wsme_arr{i}_{tag}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eids},
    )

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on"


async def test_ws_service_single_entity_string(rest, ws):
    """WS call_service with entity_id as string works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.wsme_str_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Target entity_id ────────────────────────────────────

async def test_ws_service_target_entity_string(rest, ws):
    """WS call_service with target.entity_id string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wsme_tgt_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        target={"entity_id": eid},
        service_data={},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ws_service_target_entity_array(rest, ws):
    """WS call_service with target.entity_id array."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.wsme_tgtarr{i}_{tag}" for i in range(2)]
    for eid in eids:
        await rest.set_state(eid, "on")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_off",
        target={"entity_id": eids},
        service_data={},
    )

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "off", f"{eid} should be off"


# ── Multi-entity with attributes ────────────────────────

async def test_ws_service_array_with_brightness(rest, ws):
    """WS call_service array with brightness applies to all."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.wsme_br{i}_{tag}" for i in range(2)]
    for eid in eids:
        await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eids, "brightness": 200},
    )

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"
        assert state["attributes"]["brightness"] == 200


# ── Call returns success ────────────────────────────────

async def test_ws_service_returns_success(rest, ws):
    """WS call_service returns success=true."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.wsme_succ_{tag}"
    await rest.set_state(eid, "off")

    result = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    assert result["success"] is True


async def test_ws_service_empty_entity_list(ws):
    """WS call_service with empty entity list succeeds."""
    result = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": []},
    )
    assert result["success"] is True
