"""
CTS -- WS call_service Response Format Tests

Verifies the structure of call_service responses via WebSocket,
including changed_states array, entity state fields, and multi-entity
responses.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_call_service_returns_result(ws, rest):
    """WS call_service response has 'result' field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_resp_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    assert "result" in resp


async def test_call_service_result_is_list(ws, rest):
    """call_service result is a list of changed states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_list_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    result = resp["result"]
    assert isinstance(result, list)
    assert len(result) >= 1


async def test_changed_state_has_entity_id(ws, rest):
    """Changed state entries include entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_eid_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["entity_id"] == eid


async def test_changed_state_has_state_field(ws, rest):
    """Changed state entries include 'state' string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_state_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["state"] == "on"


async def test_changed_state_has_attributes(ws, rest):
    """Changed state entries include 'attributes' dict."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_attrs_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": f"WS Test {tag}"})

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert "attributes" in entry
    assert isinstance(entry["attributes"], dict)


async def test_changed_state_has_timestamps(ws, rest):
    """Changed state entries include last_changed and last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_time_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert "last_changed" in entry
    assert "last_updated" in entry


async def test_changed_state_has_context(ws, rest):
    """Changed state entries include context with id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.ws_ctx_{tag}"
    await rest.set_state(eid, "locked")

    resp = await ws.send_command(
        "call_service",
        domain="lock",
        service="unlock",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert "context" in entry
    assert "id" in entry["context"]


async def test_multi_entity_service_response(ws, rest):
    """call_service with multiple entities returns all changed states."""
    tag = uuid.uuid4().hex[:8]
    eid_a = f"light.ws_multi_a_{tag}"
    eid_b = f"light.ws_multi_b_{tag}"
    await rest.set_state(eid_a, "off")
    await rest.set_state(eid_b, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": [eid_a, eid_b]},
    )
    assert resp["success"] is True
    result = resp["result"]
    assert len(result) == 2
    entity_ids = [e["entity_id"] for e in result]
    assert eid_a in entity_ids
    assert eid_b in entity_ids


async def test_toggle_response_reflects_new_state(ws, rest):
    """Toggle response shows the new (toggled) state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_toggle_{tag}"
    await rest.set_state(eid, "on")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["state"] == "off"


async def test_service_preserves_attributes_in_response(ws, rest):
    """Service call response preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_pres_{tag}"
    await rest.set_state(eid, "on", {"brightness": 100, "friendly_name": f"Lamp {tag}"})

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_off",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["state"] == "off"
    assert entry["attributes"].get("brightness") == 100
    assert entry["attributes"].get("friendly_name") == f"Lamp {tag}"
