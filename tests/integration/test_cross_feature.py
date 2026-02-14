"""
CTS -- Cross-Feature Integration Tests

Tests that verify multiple subsystems work together:
state machine + automations + services + WebSocket + history.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.15


# ── State Change → WS Event → History ───────────────────────

async def test_state_change_recorded_in_history(rest):
    """State change via REST is recorded in history."""
    entity = "sensor.xfeat_hist"
    await rest.set_state(entity, "initial")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(entity, "updated")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "updated" in states


async def test_service_call_appears_in_history(rest):
    """Service call that changes state is recorded in history."""
    entity = "light.xfeat_svc_hist"
    await rest.set_state(entity, "off")
    await asyncio.sleep(_FLUSH)
    await rest.call_service("light", "turn_on", {"entity_id": entity})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "on" in states


# ── Service Call → WS Event ─────────────────────────────────

async def test_service_call_triggers_ws_event(ws, rest):
    """Service call generates state_changed WS event."""
    entity = "switch.xfeat_ws_svc"
    await rest.set_state(entity, "off")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.call_service("switch", "turn_on", {"entity_id": entity})

    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == entity
    assert event["event"]["data"]["new_state"]["state"] == "on"


# ── Automation → Service → State ────────────────────────────

async def test_automation_trigger_changes_state(rest):
    """Triggering automation modifies state via service calls."""
    await rest.set_state("lock.front_door", "locked")
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.2)

    # Fire smoke automation
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)

    # Automation should have unlocked doors
    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"


# ── Scene → Service → WS ───────────────────────────────────

async def test_scene_activation_triggers_ws_events(ws, rest):
    """Scene activation triggers WS state_changed events."""
    await rest.set_state("light.living_room_main", "off")
    sub_id = await ws.subscribe_events("state_changed")

    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})

    # Should receive events for changed lights
    events = []
    for _ in range(10):
        try:
            ev = await ws.recv_event(timeout=2.0)
            events.append(ev)
        except asyncio.TimeoutError:
            break

    changed_entities = [e["event"]["data"]["entity_id"] for e in events]
    assert "light.living_room_main" in changed_entities


# ── Template + State ────────────────────────────────────────

async def test_template_reflects_service_change(rest):
    """Template rendering reflects state changed by service call."""
    entity = "sensor.xfeat_tmpl"
    await rest.set_state(entity, "50")
    await rest.call_service("homeassistant", "turn_off", {"entity_id": entity})

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": f"{{{{ states('{entity}') }}}}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "off"


# ── Area + Search + State ───────────────────────────────────

async def test_area_search_reflects_state_changes(rest):
    """Search by area returns entities with current state."""
    entity = "sensor.xfeat_area_search"
    area_id = "xfeat_room"
    await rest.set_state(entity, "42")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": "XFeat Room"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas/{area_id}/entities/{entity}",
        headers=rest._headers(),
    )

    # Update state
    await rest.set_state(entity, "99")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}",
        headers=rest._headers(),
    )
    data = resp.json()
    found = next(e for e in data if e["entity_id"] == entity)
    assert found["state"] == "99"


# ── Webhook → State → WS ───────────────────────────────────

async def test_webhook_state_triggers_ws_event(ws, rest):
    """Webhook state change triggers WS event."""
    entity = "sensor.xfeat_webhook_ws"
    await rest.set_state(entity, "idle")
    sub_id = await ws.subscribe_events("state_changed")

    await rest.client.post(
        f"{rest.base_url}/api/webhook/xfeat_hook",
        json={"entity_id": entity, "state": "active"},
    )

    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == entity
    assert event["event"]["data"]["new_state"]["state"] == "active"


# ── Logbook + Service Call ──────────────────────────────────

async def test_logbook_records_service_changes(rest):
    """Service call state changes appear in logbook."""
    entity = "light.xfeat_logbook"
    await rest.set_state(entity, "off")
    await asyncio.sleep(_FLUSH)
    await rest.call_service("light", "turn_on", {"entity_id": entity})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1


# ── Health Metrics After Operations ─────────────────────────

async def test_health_state_changes_increment(rest):
    """State changes counter increments with operations."""
    h1 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    count1 = h1["state_changes"]

    await rest.set_state("sensor.xfeat_health_counter", "tick")

    h2 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    count2 = h2["state_changes"]
    assert count2 > count1
