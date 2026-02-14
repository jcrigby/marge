"""
CTS — Extended API Tests (Phase 5+6)

Tests for history, webhook, backup, logbook, services listing, and template endpoints.
"""

import asyncio
import io
import tarfile
import time

import httpx
import pytest
import pytest_asyncio


BASE_URL = "http://localhost:8124"


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=10.0)


# ── History API ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_history_returns_list(rest):
    """GET /api/history/period/:entity_id returns a JSON array."""
    # Set state so there's at least one history entry
    await rest.set_state("sensor.history_test_1", "100", {"unit_of_measurement": "W"})
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.history_test_1",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_history_contains_expected_fields(rest):
    """History entries have entity_id, state, attributes, last_changed, last_updated."""
    await rest.set_state("sensor.history_test_2", "42")
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.history_test_2",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1

    entry = data[0]
    assert "entity_id" in entry
    assert "state" in entry
    assert "attributes" in entry
    assert "last_changed" in entry
    assert "last_updated" in entry
    assert entry["entity_id"] == "sensor.history_test_2"
    assert entry["state"] == "42"


@pytest.mark.asyncio
async def test_history_tracks_multiple_changes(rest):
    """Multiple state changes appear in history."""
    entity = "sensor.history_multi"
    await rest.set_state(entity, "10")
    await asyncio.sleep(0.3)
    await rest.set_state(entity, "20")
    await asyncio.sleep(0.3)
    await rest.set_state(entity, "30")
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "10" in states
    assert "20" in states
    assert "30" in states


@pytest.mark.asyncio
async def test_history_empty_for_unknown_entity(rest):
    """Unknown entity returns empty list, not 404."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.nonexistent_xyzzy",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Webhook API ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_sets_state(rest):
    """POST /api/webhook/:id with entity_id+state creates/updates entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook",
        json={"entity_id": "sensor.webhook_cts", "state": "triggered"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "message" in body

    # Verify state was set
    state = await rest.get_state("sensor.webhook_cts")
    assert state is not None
    assert state["state"] == "triggered"


@pytest.mark.asyncio
async def test_webhook_fires_event(rest):
    """POST /api/webhook/:id with event_type fires an event."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/event_hook",
        json={"event_type": "test_event"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "Event test_event fired" in body["message"]


@pytest.mark.asyncio
async def test_webhook_default_event(rest):
    """POST /api/webhook/:id without special keys fires webhook.<id> event."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/my_hook",
        json={"data": "hello"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "webhook.my_hook" in body["message"]


@pytest.mark.asyncio
async def test_webhook_with_attributes(rest):
    """Webhook can set state with attributes."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/attr_hook",
        json={
            "entity_id": "sensor.webhook_attrs",
            "state": "99",
            "attributes": {"unit_of_measurement": "lux", "device_class": "illuminance"},
        },
    )
    assert resp.status_code == 200

    state = await rest.get_state("sensor.webhook_attrs")
    assert state["state"] == "99"
    assert state["attributes"]["unit_of_measurement"] == "lux"


# ── Backup API ───────────────────────────────────────────


def test_backup_returns_tar_gz(client):
    """GET /api/backup returns a valid tar.gz archive."""
    resp = client.get("/api/backup")
    assert resp.status_code == 200
    assert "application/gzip" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")

    # Verify it's a valid tar.gz
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert "marge.db" in names


def test_backup_contains_config(client):
    """Backup includes automations.yaml and scenes.yaml."""
    resp = client.get("/api/backup")
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert "automations.yaml" in names
        assert "scenes.yaml" in names


def test_backup_has_filename_header(client):
    """Content-Disposition includes a timestamped filename."""
    resp = client.get("/api/backup")
    disposition = resp.headers.get("content-disposition", "")
    assert "marge_backup_" in disposition
    assert ".tar.gz" in disposition


# ── Logbook API ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_logbook_returns_state_changes(rest):
    """GET /api/logbook/:entity_id returns filtered state transitions."""
    # Use unique entity to avoid cross-contamination from prior runs
    entity = f"sensor.logbook_test_{int(time.time() * 1000) % 100000}"
    await rest.set_state(entity, "off")
    await asyncio.sleep(0.3)
    await rest.set_state(entity, "on")
    await asyncio.sleep(0.3)
    await rest.set_state(entity, "on")  # duplicate — should be filtered
    await asyncio.sleep(0.3)
    await rest.set_state(entity, "off")
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    # Should have 3 entries (off, on, off) — duplicate "on" filtered
    states = [e["state"] for e in data]
    assert states == ["off", "on", "off"]


@pytest.mark.asyncio
async def test_logbook_entries_have_when(rest):
    """Logbook entries include entity_id, state, and when fields."""
    entity = "sensor.logbook_fields"
    await rest.set_state(entity, "active")
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    entry = data[0]
    assert "entity_id" in entry
    assert "state" in entry
    assert "when" in entry


# ── Services API ────────────────────────────────────────


@pytest.mark.asyncio
async def test_services_returns_list(rest):
    """GET /api/services returns a list of service domain objects."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Each entry should have domain and services
    domains = [entry["domain"] for entry in data]
    assert "light" in domains
    assert "switch" in domains


@pytest.mark.asyncio
async def test_services_contains_expected_services(rest):
    """Services listing includes known service handlers."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light_entry = next((e for e in data if e["domain"] == "light"), None)
    assert light_entry is not None
    svcs = light_entry["services"]
    assert "turn_on" in svcs
    assert "turn_off" in svcs
    assert "toggle" in svcs


@pytest.mark.asyncio
async def test_services_input_helpers(rest):
    """Input helper services are registered."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = {e["domain"]: e["services"] for e in data}
    assert "set_value" in domains.get("input_number", {})
    assert "set_value" in domains.get("input_text", {})
    assert "select_option" in domains.get("input_select", {})


# ── Template API ────────────────────────────────────────


@pytest.mark.asyncio
async def test_template_basic_render(rest):
    """POST /api/template renders a Jinja2 template."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 1 + 2 }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "3"


@pytest.mark.asyncio
async def test_template_states_function(rest):
    """Template can access entity states via states() function."""
    await rest.set_state("sensor.template_cts", "42")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('sensor.template_cts') }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


@pytest.mark.asyncio
async def test_template_filter(rest):
    """Template supports round filter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 3.14159 | round(2) }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "3.14"


@pytest.mark.asyncio
async def test_template_invalid_returns_400(rest):
    """Invalid template returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ invalid syntax !!!"},
    )
    assert resp.status_code == 400


# ── Events API ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_events_returns_list(rest):
    """GET /api/events returns a list of event type objects."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    events = [e["event"] for e in data]
    assert "state_changed" in events
    assert "call_service" in events


# ── WebSocket call_service ──────────────────────────────


@pytest.mark.asyncio
async def test_ws_call_service(ws, rest):
    """WebSocket call_service dispatches through service registry."""
    # Create an entity first
    await rest.set_state("light.ws_test", "off")
    import json
    msg_id = 100
    await ws.ws.send(json.dumps({
        "id": msg_id,
        "type": "call_service",
        "domain": "light",
        "service": "turn_on",
        "service_data": {"entity_id": "light.ws_test"},
    }))
    result = json.loads(await ws.ws.recv())
    assert result["id"] == msg_id
    assert result["success"] is True

    # Verify state changed
    state = await rest.get_state("light.ws_test")
    assert state["state"] == "on"


@pytest.mark.asyncio
async def test_ws_fire_event(ws):
    """WebSocket fire_event returns success."""
    import json
    msg_id = 101
    await ws.ws.send(json.dumps({
        "id": msg_id,
        "type": "fire_event",
        "event_type": "test_ws_event",
    }))
    result = json.loads(await ws.ws.recv())
    assert result["id"] == msg_id
    assert result["success"] is True


# ── Input Helper Services ───────────────────────────────


@pytest.mark.asyncio
async def test_input_number_set_value(rest):
    """input_number.set_value changes entity state to the value."""
    await rest.set_state("input_number.volume", "50", {"min": 0, "max": 100, "step": 1})
    await rest.call_service("input_number", "set_value", {"entity_id": "input_number.volume", "value": 75})
    state = await rest.get_state("input_number.volume")
    assert state["state"] == "75"


@pytest.mark.asyncio
async def test_input_text_set_value(rest):
    """input_text.set_value changes entity state to the value string."""
    await rest.set_state("input_text.name", "hello")
    await rest.call_service("input_text", "set_value", {"entity_id": "input_text.name", "value": "world"})
    state = await rest.get_state("input_text.name")
    assert state["state"] == "world"


@pytest.mark.asyncio
async def test_input_select_select_option(rest):
    """input_select.select_option changes entity state to the option."""
    await rest.set_state("input_select.mode", "auto", {"options": ["auto", "heat", "cool"]})
    await rest.call_service("input_select", "select_option", {"entity_id": "input_select.mode", "option": "cool"})
    state = await rest.get_state("input_select.mode")
    assert state["state"] == "cool"


# ── Alarm Control Panel Services ────────────────────────


@pytest.mark.asyncio
async def test_alarm_arm_home(rest):
    """alarm_control_panel.arm_home sets state to armed_home."""
    await rest.set_state("alarm_control_panel.test", "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": "alarm_control_panel.test"})
    state = await rest.get_state("alarm_control_panel.test")
    assert state["state"] == "armed_home"


@pytest.mark.asyncio
async def test_alarm_disarm(rest):
    """alarm_control_panel.disarm sets state to disarmed."""
    await rest.set_state("alarm_control_panel.test2", "armed_away")
    await rest.call_service("alarm_control_panel", "disarm", {"entity_id": "alarm_control_panel.test2"})
    state = await rest.get_state("alarm_control_panel.test2")
    assert state["state"] == "disarmed"


# ── Cover Position Services ─────────────────────────────


@pytest.mark.asyncio
async def test_cover_set_position(rest):
    """cover.set_cover_position sets position attribute and state."""
    await rest.set_state("cover.garage", "closed")
    await rest.call_service("cover", "set_cover_position", {"entity_id": "cover.garage", "position": 50})
    state = await rest.get_state("cover.garage")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 50


@pytest.mark.asyncio
async def test_fan_set_percentage(rest):
    """fan.set_percentage sets speed and turns on the fan."""
    await rest.set_state("fan.ceiling", "off")
    await rest.call_service("fan", "set_percentage", {"entity_id": "fan.ceiling", "percentage": 75})
    state = await rest.get_state("fan.ceiling")
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75


# ── Automation Config API ──────────────────────────────


@pytest.mark.asyncio
async def test_automation_config_returns_list(rest):
    """GET /api/config/automation/config returns a list of automations."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Each entry should have id, alias, and trigger info
    auto = data[0]
    assert "id" in auto
    assert "alias" in auto
    assert "trigger_count" in auto
    assert "action_count" in auto
    assert "enabled" in auto


@pytest.mark.asyncio
async def test_automation_config_has_metadata(rest):
    """Automation config includes runtime metadata fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "total_triggers" in auto
    assert isinstance(auto["total_triggers"], int)
    assert "last_triggered" in auto
    assert "mode" in auto


@pytest.mark.asyncio
async def test_automation_reload(rest):
    """POST /api/config/core/reload reloads automations successfully."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"
    assert data["automations_reloaded"] >= 1


@pytest.mark.asyncio
async def test_automation_entity_has_friendly_name(rest):
    """Automation entities have friendly_name attribute set from alias."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    if len(automations) == 0:
        pytest.skip("No automations loaded")
    auto = automations[0]

    state = await rest.get_state(f"automation.{auto['id']}")
    assert state is not None
    assert "friendly_name" in state["attributes"]
    assert state["attributes"]["friendly_name"] == auto["alias"]


@pytest.mark.asyncio
async def test_automation_trigger_updates_metadata(rest):
    """Triggering an automation updates last_triggered and current count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    if len(automations) == 0:
        pytest.skip("No automations loaded")
    auto = automations[0]
    initial_count = auto["total_triggers"]

    # Trigger the automation
    await rest.call_service("automation", "trigger", {"entity_id": f"automation.{auto['id']}"})
    await asyncio.sleep(0.5)

    # Check metadata was updated
    resp2 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    updated = next(a for a in resp2.json() if a["id"] == auto["id"])
    assert updated["total_triggers"] == initial_count + 1
    assert updated["last_triggered"] is not None


# ── WebSocket get_config ──────────────────────────────


@pytest.mark.asyncio
async def test_ws_get_config(ws):
    """WebSocket get_config returns system configuration."""
    import json
    msg_id = 200
    await ws.ws.send(json.dumps({
        "id": msg_id,
        "type": "get_config",
    }))
    result = json.loads(await ws.ws.recv())
    assert result["id"] == msg_id
    assert result["success"] is True
    config = result["result"]
    assert "location_name" in config
    assert "version" in config
    assert "time_zone" in config
    assert "latitude" in config


# ── Scene Config API ──────────────────────────────────


@pytest.mark.asyncio
async def test_scene_config_returns_list(rest):
    """GET /api/config/scene/config returns a list of scenes."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    scene = data[0]
    assert "id" in scene
    assert "name" in scene
    assert "entity_count" in scene
    assert "entities" in scene


@pytest.mark.asyncio
async def test_scene_entity_has_friendly_name(rest):
    """Scene entities have friendly_name attribute set from scene name."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    if len(scenes) == 0:
        pytest.skip("No scenes loaded")
    scene = scenes[0]

    state = await rest.get_state(f"scene.{scene['id']}")
    assert state is not None
    assert "friendly_name" in state["attributes"]
    assert state["attributes"]["friendly_name"] == scene["name"]


# ── Prometheus Metrics ─────────────────────────────────


def test_prometheus_metrics(client):
    """GET /metrics returns Prometheus-compatible text format."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    text = resp.text
    assert "marge_entity_count" in text
    assert "marge_state_changes_total" in text
    assert "marge_memory_rss_bytes" in text
    assert "marge_uptime_seconds" in text
    assert "marge_latency_avg_microseconds" in text


def test_prometheus_metrics_automation_counts(client):
    """Prometheus metrics include per-automation trigger counts."""
    resp = client.get("/metrics")
    text = resp.text
    assert "marge_automation_triggers_total" in text


# ── Automation Enable/Disable ──────────────────────────


@pytest.mark.asyncio
async def test_automation_turn_off_disables(rest):
    """automation.turn_off disables an automation (state becomes off)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    if not automations:
        pytest.skip("No automations loaded")
    auto = automations[0]

    await rest.call_service("automation", "turn_off", {"entity_id": f"automation.{auto['id']}"})
    state = await rest.get_state(f"automation.{auto['id']}")
    assert state["state"] == "off"

    # Re-enable for other tests
    await rest.call_service("automation", "turn_on", {"entity_id": f"automation.{auto['id']}"})
    state = await rest.get_state(f"automation.{auto['id']}")
    assert state["state"] == "on"


@pytest.mark.asyncio
async def test_automation_toggle(rest):
    """automation.toggle toggles the enabled state."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    if not automations:
        pytest.skip("No automations loaded")
    auto = automations[0]

    # Toggle off
    await rest.call_service("automation", "toggle", {"entity_id": f"automation.{auto['id']}"})
    state = await rest.get_state(f"automation.{auto['id']}")
    first_state = state["state"]

    # Toggle back
    await rest.call_service("automation", "toggle", {"entity_id": f"automation.{auto['id']}"})
    state = await rest.get_state(f"automation.{auto['id']}")
    second_state = state["state"]

    assert first_state != second_state


# ── Statistics API ──────────────────────────────────────


@pytest.mark.asyncio
async def test_statistics_returns_list(rest):
    """GET /api/statistics/:entity_id returns hourly aggregated stats."""
    entity = "sensor.stats_test"
    # Set some numeric states
    for val in ["10", "20", "30", "40", "50"]:
        await rest.set_state(entity, val)
        await asyncio.sleep(0.2)
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    bucket = data[0]
    assert "hour" in bucket
    assert "min" in bucket
    assert "max" in bucket
    assert "mean" in bucket
    assert "count" in bucket
    assert bucket["min"] >= 10
    assert bucket["max"] <= 50
    assert bucket["count"] >= 5


@pytest.mark.asyncio
async def test_statistics_empty_for_non_numeric(rest):
    """Non-numeric entities return empty statistics."""
    await rest.set_state("sensor.text_stat", "hello")
    await asyncio.sleep(0.5)
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.text_stat",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Automation Services in /api/services ────────────────


# ── Area Management API ─────────────────────────────────


@pytest.mark.asyncio
async def test_area_crud(rest):
    """Areas can be created, listed, and deleted."""
    # Create
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "cts_test_room", "name": "CTS Test Room"},
    )
    assert resp.status_code == 200

    # List
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    areas = resp.json()
    assert any(a["area_id"] == "cts_test_room" for a in areas)

    # Delete
    resp = await rest.client.delete(
        f"{rest.base_url}/api/areas/cts_test_room",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify deleted
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    areas = resp.json()
    assert not any(a["area_id"] == "cts_test_room" for a in areas)


@pytest.mark.asyncio
async def test_area_entity_assignment(rest):
    """Entities can be assigned to and unassigned from areas."""
    # Setup
    await rest.set_state("light.area_test", "on")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "cts_assign_room", "name": "Assign Room"},
    )

    # Assign
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/cts_assign_room/entities/light.area_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Check area entities
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/cts_assign_room/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entities = resp.json()
    assert len(entities) >= 1
    assert any(e.get("entity_id") == "light.area_test" for e in entities)

    # Unassign
    resp = await rest.client.delete(
        f"{rest.base_url}/api/areas/cts_assign_room/entities/light.area_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/areas/cts_assign_room",
        headers=rest._headers(),
    )


@pytest.mark.asyncio
async def test_services_includes_automation(rest):
    """Services listing includes automation domain with trigger/turn_on/turn_off."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    auto_entry = next((e for e in data if e["domain"] == "automation"), None)
    assert auto_entry is not None
    svcs = auto_entry["services"]
    assert "trigger" in svcs
    assert "turn_on" in svcs
    assert "turn_off" in svcs
    assert "toggle" in svcs


# ── Long-Lived Access Tokens ──────────────────────────


@pytest.mark.asyncio
async def test_token_crud(rest):
    """Tokens can be created, listed, and deleted."""
    # Create
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": "CTS Test Token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "token" in data  # only shown on creation
    assert data["name"] == "CTS Test Token"
    assert data["token"].startswith("marge_")
    token_id = data["id"]

    # List
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert any(t["id"] == token_id for t in tokens)
    # Token values should NOT be exposed in listing
    for t in tokens:
        assert t.get("token") is None

    # Delete
    resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify deleted
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    tokens = resp.json()
    assert not any(t["id"] == token_id for t in tokens)


@pytest.mark.asyncio
async def test_token_delete_nonexistent_returns_404(rest):
    """Deleting a nonexistent token returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/tok_nonexistent",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Template with state_attr ────────────────────────


@pytest.mark.asyncio
async def test_template_state_attr(rest):
    """Template can access entity attributes via state_attr()."""
    await rest.set_state("sensor.attr_cts", "72", {"unit_of_measurement": "F", "device_class": "temperature"})
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ state_attr('sensor.attr_cts', 'unit_of_measurement') }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "F"


@pytest.mark.asyncio
async def test_template_is_state(rest):
    """Template is_state() returns true/false."""
    await rest.set_state("light.is_state_cts", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ is_state('light.is_state_cts', 'on') }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


# ── Health endpoint ─────────────────────────────────


def test_health_response_fields(client):
    """GET /api/health returns all expected metric fields."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "entity_count" in data
    assert "memory_rss_mb" in data
    assert "startup_ms" in data
    assert "latency_avg_us" in data
    assert "state_changes" in data
    assert "uptime_seconds" in data


def test_health_startup_under_5ms(client):
    """Marge starts up in under 5ms."""
    resp = client.get("/api/health")
    data = resp.json()
    assert data["startup_ms"] < 5.0, f"Startup took {data['startup_ms']}ms"


# ── Climate and Cover Services ──────────────────────


@pytest.mark.asyncio
async def test_climate_set_temperature(rest):
    """climate.set_temperature sets target temperature attribute."""
    await rest.set_state("climate.thermostat_cts", "heat", {"temperature": 20})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": "climate.thermostat_cts",
        "temperature": 22.5,
    })
    state = await rest.get_state("climate.thermostat_cts")
    assert state["attributes"]["temperature"] == 22.5


@pytest.mark.asyncio
async def test_climate_set_hvac_mode(rest):
    """climate.set_hvac_mode changes entity state to the mode."""
    await rest.set_state("climate.mode_cts", "off")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": "climate.mode_cts",
        "hvac_mode": "cool",
    })
    state = await rest.get_state("climate.mode_cts")
    assert state["state"] == "cool"


@pytest.mark.asyncio
async def test_lock_services(rest):
    """lock.lock and lock.unlock toggle lock state."""
    await rest.set_state("lock.cts_lock", "unlocked")
    await rest.call_service("lock", "lock", {"entity_id": "lock.cts_lock"})
    state = await rest.get_state("lock.cts_lock")
    assert state["state"] == "locked"

    await rest.call_service("lock", "unlock", {"entity_id": "lock.cts_lock"})
    state = await rest.get_state("lock.cts_lock")
    assert state["state"] == "unlocked"


@pytest.mark.asyncio
async def test_input_boolean_toggle(rest):
    """input_boolean.toggle flips on/off state."""
    await rest.set_state("input_boolean.cts_toggle", "off")
    await rest.call_service("input_boolean", "toggle", {"entity_id": "input_boolean.cts_toggle"})
    state = await rest.get_state("input_boolean.cts_toggle")
    assert state["state"] == "on"

    await rest.call_service("input_boolean", "toggle", {"entity_id": "input_boolean.cts_toggle"})
    state = await rest.get_state("input_boolean.cts_toggle")
    assert state["state"] == "off"


# ── Config Endpoint ─────────────────────────────────


# ── Device Registry ──────────────────────────────────


@pytest.mark.asyncio
async def test_device_crud(rest):
    """Devices can be created, listed, and deleted."""
    # Create
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={
            "device_id": "cts_dev_001",
            "name": "CTS Test Device",
            "manufacturer": "Acme",
            "model": "Widget v2",
        },
    )
    assert resp.status_code == 200

    # List
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    devices = resp.json()
    dev = next((d for d in devices if d["device_id"] == "cts_dev_001"), None)
    assert dev is not None
    assert dev["name"] == "CTS Test Device"
    assert dev["manufacturer"] == "Acme"
    assert dev["model"] == "Widget v2"

    # Delete
    resp = await rest.client.delete(
        f"{rest.base_url}/api/devices/cts_dev_001",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_device_entity_assignment(rest):
    """Entities can be assigned to devices."""
    await rest.set_state("sensor.dev_cts", "42")
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": "cts_dev_assign", "name": "Assign Device"},
    )

    # Assign entity
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/cts_dev_assign/entities/sensor.dev_cts",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify in device listing
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    devices = resp.json()
    dev = next((d for d in devices if d["device_id"] == "cts_dev_assign"), None)
    assert dev is not None
    assert "sensor.dev_cts" in dev["entities"]
    assert dev["entity_count"] == 1

    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/devices/cts_dev_assign",
        headers=rest._headers(),
    )


def test_config_response(client):
    """GET /api/config returns location and unit system."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "location_name" in data
    assert "latitude" in data
    assert "longitude" in data
    assert "unit_system" in data
    assert "time_zone" in data
    assert "version" in data
    assert "state" in data
    assert data["state"] == "RUNNING"


# ── Automation YAML API ──────────────────────────────────


def test_automation_yaml_read(client):
    """GET /api/config/automation/yaml returns the raw YAML."""
    resp = client.get("/api/config/automation/yaml")
    assert resp.status_code == 200
    assert "text/yaml" in resp.headers.get("content-type", "")
    text = resp.text
    assert "id:" in text
    assert "triggers:" in text or "trigger:" in text


def test_automation_yaml_write_and_reload(client):
    """PUT /api/config/automation/yaml validates, saves, and reloads."""
    # Read original
    resp = client.get("/api/config/automation/yaml")
    original = resp.text

    # Write back (same content)
    resp = client.put(
        "/api/config/automation/yaml",
        content=original,
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"
    assert data["automations_reloaded"] >= 1


def test_automation_yaml_reject_invalid(client):
    """PUT /api/config/automation/yaml rejects invalid YAML."""
    resp = client.put(
        "/api/config/automation/yaml",
        content="[{invalid yaml: - - -",
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 400


# ── Entity create/delete lifecycle ───────────────────────


@pytest.mark.asyncio
async def test_entity_delete(rest):
    """DELETE on a state removes the entity."""
    # Create
    await rest.client.post(
        f"{rest.base_url}/api/states/sensor.to_delete",
        headers=rest._headers(),
        json={"state": "temporary", "attributes": {}},
    )
    # Verify exists
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.to_delete",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Delete
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.to_delete",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify gone
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.to_delete",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_entity_delete_nonexistent(rest):
    """DELETE on a nonexistent entity returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.does_not_exist_at_all",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Automation trigger via REST ──────────────────────────


def test_automation_trigger_via_service(client):
    """POST /api/services/automation/trigger fires an automation."""
    # Get first automation ID
    resp = client.get("/api/config/automation/config")
    autos = resp.json()
    if not autos:
        pytest.skip("No automations loaded")
    auto_id = autos[0]["id"]
    initial_count = autos[0]["total_triggers"]

    # Trigger
    resp = client.post(
        "/api/services/automation/trigger",
        json={"entity_id": f"automation.{auto_id}"},
    )
    assert resp.status_code == 200

    # Verify count increased
    time.sleep(0.5)
    resp = client.get("/api/config/automation/config")
    updated = resp.json()
    auto = next(a for a in updated if a["id"] == auto_id)
    assert auto["total_triggers"] >= initial_count + 1


# ── WebSocket ping/pong ─────────────────────────────────


@pytest.mark.asyncio
async def test_websocket_ping_pong():
    """WebSocket ping type returns a response with matching id."""
    import websockets

    async with websockets.connect("ws://localhost:8124/api/websocket") as ws:
        # Handle auth
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        import json
        data = json.loads(msg)
        if data["type"] == "auth_required":
            await ws.send(json.dumps({"type": "auth", "access_token": ""}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)

        # Send ping
        await ws.send(json.dumps({"id": 99, "type": "ping"}))
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(msg)
        assert data["id"] == 99
        assert data["type"] == "pong"


# ── Fire custom event ────────────────────────────────────


def test_fire_event_rest(client):
    """POST /api/events/:event_type fires an event."""
    resp = client.post(
        "/api/events/cts_test_event",
        json={"payload": "hello"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("message", "").startswith("Event") or "ok" in str(data).lower()


# ── Service listing ──────────────────────────────────────


def test_services_list_contains_common_domains(client):
    """GET /api/services includes standard domains."""
    resp = client.get("/api/services")
    assert resp.status_code == 200
    data = resp.json()
    # Should be a list of domain objects
    assert isinstance(data, list)
    domains = [d.get("domain", "") for d in data]
    assert "light" in domains
    assert "switch" in domains


@pytest.mark.asyncio
async def test_websocket_get_services():
    """WebSocket get_services returns service domains."""
    import websockets
    import json

    async with websockets.connect("ws://localhost:8124/api/websocket") as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(msg)
        if data["type"] == "auth_required":
            await ws.send(json.dumps({"type": "auth", "access_token": ""}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)

        await ws.send(json.dumps({"id": 10, "type": "get_services"}))
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(msg)
        assert data["id"] == 10
        assert data["success"] is True
        services = data["result"]
        assert isinstance(services, list)
        domains = [s["domain"] for s in services]
        assert "light" in domains


@pytest.mark.asyncio
async def test_websocket_get_config():
    """WebSocket get_config returns location and version."""
    import websockets
    import json

    async with websockets.connect("ws://localhost:8124/api/websocket") as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(msg)
        if data["type"] == "auth_required":
            await ws.send(json.dumps({"type": "auth", "access_token": ""}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)

        await ws.send(json.dumps({"id": 11, "type": "get_config"}))
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(msg)
        assert data["id"] == 11
        assert data["success"] is True
        config = data["result"]
        assert "location_name" in config
        assert "version" in config
        assert "latitude" in config


# ── Scene YAML API ───────────────────────────────────────


def test_scene_yaml_read(client):
    """GET /api/config/scene/yaml returns raw YAML."""
    resp = client.get("/api/config/scene/yaml")
    assert resp.status_code == 200
    assert "text/yaml" in resp.headers.get("content-type", "")
    text = resp.text
    assert "id:" in text
    assert "entities:" in text


def test_scene_yaml_roundtrip(client):
    """PUT /api/config/scene/yaml saves and returns ok."""
    resp = client.get("/api/config/scene/yaml")
    original = resp.text

    resp = client.put(
        "/api/config/scene/yaml",
        content=original,
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"


# ── Global Logbook ───────────────────────────────────────


def test_logbook_global(client):
    """GET /api/logbook returns recent state changes across all entities."""
    resp = client.get("/api/logbook")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── Concurrent state updates ─────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_state_writes():
    """Concurrent state writes don't corrupt data."""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8124", timeout=10.0) as client:
        tasks = []
        for i in range(20):
            tasks.append(
                client.post(
                    f"/api/states/sensor.concurrent_{i}",
                    json={"state": str(i), "attributes": {}},
                )
            )
        results = await asyncio.gather(*tasks)
        for r in results:
            assert r.status_code in (200, 201)

        # Verify all 20 entities exist
        resp = await client.get("/api/states")
        states = resp.json()
        concurrent_ids = [s["entity_id"] for s in states if s["entity_id"].startswith("sensor.concurrent_")]
        assert len(concurrent_ids) >= 20


# ── Label Registry ─────────────────────────────────────


def test_label_crud(client):
    """Create, list, and delete a label."""
    # Create
    r = client.post("/api/labels", json={"label_id": "test_critical", "name": "Critical", "color": "#e55"})
    assert r.status_code == 200

    # List and verify
    r = client.get("/api/labels")
    assert r.status_code == 200
    labels = r.json()
    found = [l for l in labels if l["label_id"] == "test_critical"]
    assert len(found) == 1
    assert found[0]["name"] == "Critical"
    assert found[0]["color"] == "#e55"

    # Delete
    r = client.request("DELETE", "/api/labels/test_critical")
    assert r.status_code == 200

    # Verify gone
    r = client.get("/api/labels")
    labels = r.json()
    found = [l for l in labels if l["label_id"] == "test_critical"]
    assert len(found) == 0


def test_label_entity_assignment(client):
    """Assign and unassign labels to entities."""
    # Setup: create a label and an entity
    client.post("/api/labels", json={"label_id": "test_urgent", "name": "Urgent", "color": "#f80"})
    client.post("/api/states/sensor.label_test", json={"state": "42", "attributes": {}})

    # Assign
    r = client.post("/api/labels/test_urgent/entities/sensor.label_test")
    assert r.status_code == 200

    # Verify label has entity
    r = client.get("/api/labels")
    labels = r.json()
    urgent = [l for l in labels if l["label_id"] == "test_urgent"]
    assert len(urgent) == 1
    assert "sensor.label_test" in urgent[0]["entities"]
    assert urgent[0]["entity_count"] == 1

    # Unassign
    r = client.request("DELETE", "/api/labels/test_urgent/entities/sensor.label_test")
    assert r.status_code == 200

    # Verify empty
    r = client.get("/api/labels")
    labels = r.json()
    urgent = [l for l in labels if l["label_id"] == "test_urgent"]
    assert urgent[0]["entity_count"] == 0

    # Cleanup
    client.request("DELETE", "/api/labels/test_urgent")


def test_label_missing_fields(client):
    """Creating a label without required fields returns 400."""
    r = client.post("/api/labels", json={"label_id": "test_bad"})
    assert r.status_code == 400

    r = client.post("/api/labels", json={"name": "No ID"})
    assert r.status_code == 400


def test_label_color_optional(client):
    """Creating a label without color defaults to empty string."""
    client.post("/api/labels", json={"label_id": "test_no_color", "name": "No Color"})

    r = client.get("/api/labels")
    labels = r.json()
    found = [l for l in labels if l["label_id"] == "test_no_color"]
    assert len(found) == 1
    assert found[0]["color"] == ""

    # Cleanup
    client.request("DELETE", "/api/labels/test_no_color")


# ── Additional Error Path Tests ────────────────────────


def test_set_state_missing_body(client):
    """POST /api/states/:entity_id without a body returns 4xx."""
    r = client.post("/api/states/sensor.no_body", content=b"")
    assert r.status_code in (400, 415, 422)


def test_call_service_unknown_domain(client):
    """Calling a service on an unknown domain returns 200 (no-op, HA-compatible)."""
    r = client.post("/api/services/nonexistent_domain/turn_on", json={"entity_id": "light.fake"})
    assert r.status_code == 200


def test_fire_event_returns_ok(client):
    """POST /api/events/:event_type fires and returns OK."""
    r = client.post("/api/events/test_label_event", json={"data": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("message") is not None or body.get("result") is not None


def test_health_fields_complete(client):
    """Health endpoint returns all expected fields."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    for field in ["status", "version", "entity_count", "memory_rss_mb",
                   "uptime_seconds", "startup_ms", "state_changes",
                   "latency_avg_us", "latency_max_us"]:
        assert field in data, f"Missing health field: {field}"


# ── Entity Search API ─────────────────────────────────


def test_search_by_domain(client):
    """Search entities filtered by domain."""
    # Ensure at least one light exists
    client.post("/api/states/light.search_test", json={"state": "on", "attributes": {}})
    client.post("/api/states/sensor.search_temp", json={"state": "22.5", "attributes": {}})

    r = client.get("/api/states/search", params={"domain": "light"})
    assert r.status_code == 200
    results = r.json()
    assert all(e["entity_id"].startswith("light.") for e in results)
    assert any(e["entity_id"] == "light.search_test" for e in results)


def test_search_by_state(client):
    """Search entities filtered by state value."""
    client.post("/api/states/switch.search_on", json={"state": "on", "attributes": {}})
    client.post("/api/states/switch.search_off", json={"state": "off", "attributes": {}})

    r = client.get("/api/states/search", params={"state": "on"})
    assert r.status_code == 200
    results = r.json()
    assert all(e["state"] == "on" for e in results)


def test_search_by_text(client):
    """Search entities by text query (entity_id, state, friendly_name)."""
    client.post("/api/states/sensor.search_textmatch", json={
        "state": "42",
        "attributes": {"friendly_name": "Kitchen Temperature"},
    })

    # Search by friendly_name
    r = client.get("/api/states/search", params={"q": "kitchen"})
    assert r.status_code == 200
    results = r.json()
    assert any(e["entity_id"] == "sensor.search_textmatch" for e in results)

    # Search by entity_id fragment
    r = client.get("/api/states/search", params={"q": "textmatch"})
    assert r.status_code == 200
    results = r.json()
    assert any(e["entity_id"] == "sensor.search_textmatch" for e in results)


def test_search_combined_filters(client):
    """Search with multiple filters applied simultaneously."""
    client.post("/api/states/light.combo_on", json={"state": "on", "attributes": {}})
    client.post("/api/states/light.combo_off", json={"state": "off", "attributes": {}})

    r = client.get("/api/states/search", params={"domain": "light", "state": "on"})
    assert r.status_code == 200
    results = r.json()
    assert all(e["entity_id"].startswith("light.") for e in results)
    assert all(e["state"] == "on" for e in results)


def test_search_no_results(client):
    """Search with no matching entities returns empty list."""
    r = client.get("/api/states/search", params={"q": "zzznonexistent999"})
    assert r.status_code == 200
    results = r.json()
    assert results == []


def test_search_by_label(client):
    """Search entities filtered by label."""
    # Setup: create label and assign entity
    client.post("/api/labels", json={"label_id": "search_test_lbl", "name": "Search Test"})
    client.post("/api/states/sensor.lbl_search", json={"state": "10", "attributes": {}})
    client.post("/api/labels/search_test_lbl/entities/sensor.lbl_search")

    r = client.get("/api/states/search", params={"label": "search_test_lbl"})
    assert r.status_code == 200
    results = r.json()
    assert any(e["entity_id"] == "sensor.lbl_search" for e in results)

    # Cleanup
    client.request("DELETE", "/api/labels/search_test_lbl")


def test_search_results_sorted(client):
    """Search results are sorted by entity_id."""
    r = client.get("/api/states/search")
    assert r.status_code == 200
    results = r.json()
    ids = [e["entity_id"] for e in results]
    assert ids == sorted(ids)


# ── Persistent Notifications ──────────────────────────


def test_notification_create_via_service(client):
    """Create a notification via persistent_notification.create service."""
    r = client.post("/api/services/persistent_notification/create", json={
        "notification_id": "test_notif_1",
        "title": "Test Alert",
        "message": "This is a test notification",
    })
    assert r.status_code == 200

    # Verify it appears in the list
    r = client.get("/api/notifications")
    assert r.status_code == 200
    notifs = r.json()
    found = [n for n in notifs if n["notification_id"] == "test_notif_1"]
    assert len(found) == 1
    assert found[0]["title"] == "Test Alert"
    assert found[0]["message"] == "This is a test notification"
    assert found[0]["dismissed"] is False


def test_notification_dismiss(client):
    """Dismiss a single notification."""
    # Ensure it exists
    client.post("/api/services/persistent_notification/create", json={
        "notification_id": "test_notif_dismiss",
        "title": "Dismiss Me",
        "message": "Will be dismissed",
    })

    r = client.post("/api/notifications/test_notif_dismiss/dismiss")
    assert r.status_code == 200

    # Verify it's gone from active list
    r = client.get("/api/notifications")
    notifs = r.json()
    found = [n for n in notifs if n["notification_id"] == "test_notif_dismiss"]
    assert len(found) == 0


def test_notification_dismiss_all(client):
    """Dismiss all notifications at once."""
    # Create multiple
    for i in range(3):
        client.post("/api/services/persistent_notification/create", json={
            "notification_id": f"test_dismiss_all_{i}",
            "title": f"Batch {i}",
            "message": f"Batch notification {i}",
        })

    r = client.post("/api/notifications/dismiss_all")
    assert r.status_code == 200

    # Verify all gone
    r = client.get("/api/notifications")
    notifs = r.json()
    batch = [n for n in notifs if n["notification_id"].startswith("test_dismiss_all_")]
    assert len(batch) == 0


def test_notification_dismiss_nonexistent(client):
    """Dismissing a nonexistent notification returns 404."""
    r = client.post("/api/notifications/nonexistent_notif_999/dismiss")
    assert r.status_code == 404


def test_notification_service_dismiss(client):
    """Dismiss via persistent_notification.dismiss service."""
    client.post("/api/services/persistent_notification/create", json={
        "notification_id": "test_svc_dismiss",
        "title": "Service Dismiss",
        "message": "Dismissed via service",
    })

    r = client.post("/api/services/persistent_notification/dismiss", json={
        "notification_id": "test_svc_dismiss",
    })
    assert r.status_code == 200

    r = client.get("/api/notifications")
    notifs = r.json()
    found = [n for n in notifs if n["notification_id"] == "test_svc_dismiss"]
    assert len(found) == 0


# ── WebSocket Extended Commands ───────────────────────


@pytest.mark.asyncio
async def test_ws_get_notifications(ws):
    """WebSocket get_notifications command."""
    result = await ws.send_command("get_notifications")
    assert result.get("success", False)
    assert isinstance(result.get("result"), list)


@pytest.mark.asyncio
async def test_ws_entity_registry(ws):
    """WebSocket config/entity_registry/list command."""
    result = await ws.send_command("config/entity_registry/list")
    assert result.get("success", False)
    entries = result.get("result", [])
    assert isinstance(entries, list)
    if entries:
        assert "entity_id" in entries[0]
        assert "name" in entries[0]


@pytest.mark.asyncio
async def test_ws_area_registry(ws):
    """WebSocket config/area_registry/list command."""
    result = await ws.send_command("config/area_registry/list")
    assert result.get("success", False)
    entries = result.get("result", [])
    assert isinstance(entries, list)


# ── Scene Activation ─────────────────────────────────


def test_scene_activation_via_service(client):
    """POST /api/services/scene/turn_on activates a scene."""
    # Get first scene ID
    resp = client.get("/api/config/scene/config")
    scenes = resp.json()
    if not scenes:
        pytest.skip("No scenes loaded")
    scene_id = scenes[0]["id"]

    r = client.post("/api/services/scene/turn_on", json={
        "entity_id": f"scene.{scene_id}",
    })
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_scene_config_has_entities(rest):
    """Scene config includes entity IDs affected by the scene."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    if not scenes:
        pytest.skip("No scenes loaded")
    scene = scenes[0]
    assert scene["entity_count"] > 0
    assert len(scene["entities"]) == scene["entity_count"]


# ── Area Entity Listing ──────────────────────────────


@pytest.mark.asyncio
async def test_area_entity_listing_includes_state(rest):
    """GET /api/areas/:id/entities returns full entity state objects."""
    await rest.set_state("sensor.area_state_test", "55", {"unit_of_measurement": "W"})
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "cts_state_room", "name": "State Room"},
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas/cts_state_room/entities/sensor.area_state_test",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/cts_state_room/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entities = resp.json()
    found = next((e for e in entities if e.get("entity_id") == "sensor.area_state_test"), None)
    assert found is not None
    assert found["state"] == "55"

    # Cleanup
    await rest.client.delete(f"{rest.base_url}/api/areas/cts_state_room/entities/sensor.area_state_test",
                              headers=rest._headers())
    await rest.client.delete(f"{rest.base_url}/api/areas/cts_state_room", headers=rest._headers())


# ── Device Missing Fields ────────────────────────────


def test_device_missing_name_returns_400(client):
    """Creating a device without name returns 400."""
    r = client.post("/api/devices", json={"device_id": "bad_dev"})
    assert r.status_code == 400


def test_device_missing_id_returns_400(client):
    """Creating a device without device_id returns 400."""
    r = client.post("/api/devices", json={"name": "No ID Device"})
    assert r.status_code == 400


# ── Area Missing Fields ──────────────────────────────


def test_area_missing_name_returns_400(client):
    """Creating an area without name returns 400."""
    r = client.post("/api/areas", json={"area_id": "bad_area"})
    assert r.status_code == 400


def test_area_missing_id_returns_400(client):
    """Creating an area without area_id returns 400."""
    r = client.post("/api/areas", json={"name": "No ID Area"})
    assert r.status_code == 400


# ── API Root ─────────────────────────────────────────


def test_api_root_returns_running(client):
    """GET /api/ returns the API running message."""
    r = client.get("/api/")
    assert r.status_code == 200
    data = r.json()
    assert data["message"] == "API running."


# ── Config Detailed Fields ───────────────────────────


def test_config_unit_system(client):
    """GET /api/config unit_system contains expected keys."""
    r = client.get("/api/config")
    data = r.json()
    units = data["unit_system"]
    assert "length" in units
    assert "mass" in units
    assert "temperature" in units
    assert "volume" in units


# ── Entity State Response ────────────────────────────


@pytest.mark.asyncio
async def test_set_state_returns_entity(rest):
    """POST /api/states/:entity_id returns the full entity state."""
    result = await rest.set_state("sensor.set_state_resp", "42", {"unit_of_measurement": "dB"})
    assert result["entity_id"] == "sensor.set_state_resp"
    assert result["state"] == "42"
    assert "last_changed" in result
    assert "last_updated" in result
    assert result["attributes"]["unit_of_measurement"] == "dB"


# ── History Time Filtering ───────────────────────────


@pytest.mark.asyncio
async def test_history_respects_time_range(rest):
    """History endpoint filters by start/end time parameters."""
    entity = "sensor.time_filter_test"
    await rest.set_state(entity, "100")
    await asyncio.sleep(0.5)

    # Query for a future time range — should return empty
    future = "2099-01-01T00:00:00Z"
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
        params={"start": future, "end": future},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Notification Auto-ID ─────────────────────────────


def test_notification_auto_generated_id(client):
    """Creating a notification without ID generates one automatically."""
    r = client.post("/api/services/persistent_notification/create", json={
        "title": "Auto ID",
        "message": "Should get an auto-generated ID",
    })
    assert r.status_code == 200

    # Verify it appears in listing
    r = client.get("/api/notifications")
    notifs = r.json()
    auto = [n for n in notifs if n["title"] == "Auto ID"]
    assert len(auto) >= 1
    assert len(auto[0]["notification_id"]) > 0

    # Cleanup
    for n in auto:
        client.post(f"/api/notifications/{n['notification_id']}/dismiss")


# ── WS State Change Subscription ─────────────────────


@pytest.mark.asyncio
async def test_ws_subscribe_receives_state_change(ws, rest):
    """Subscribe to state_changed events and receive one on state change."""
    sub_id = await ws.subscribe_events("state_changed")
    assert sub_id > 0

    # Trigger a state change
    await rest.set_state("sensor.ws_sub_test", "triggered")

    # Should receive the state_changed event
    event = await ws.recv_event(timeout=5.0)
    assert event["type"] == "event"
    assert event["event"]["event_type"] == "state_changed"
    assert event["event"]["data"]["new_state"]["entity_id"] == "sensor.ws_sub_test"


# ── WS Get States ───────────────────────────────────


@pytest.mark.asyncio
async def test_ws_get_states_returns_entities(ws, rest):
    """WebSocket get_states returns all current entity states."""
    # Ensure at least one entity exists
    await rest.set_state("sensor.ws_states_test", "123")

    states = await ws.get_states()
    assert isinstance(states, list)
    assert len(states) > 0
    entity_ids = [s["entity_id"] for s in states]
    assert "sensor.ws_states_test" in entity_ids


# ── Multiple Service Targets ─────────────────────────


@pytest.mark.asyncio
async def test_service_targets_array(rest):
    """Service call with entity_id as array targets multiple entities."""
    await rest.set_state("light.multi_a", "off")
    await rest.set_state("light.multi_b", "off")

    await rest.call_service("light", "turn_on", {
        "entity_id": ["light.multi_a", "light.multi_b"],
    })

    state_a = await rest.get_state("light.multi_a")
    state_b = await rest.get_state("light.multi_b")
    assert state_a["state"] == "on"
    assert state_b["state"] == "on"


# ── WS Device Registry ─────────────────────────────


@pytest.mark.asyncio
async def test_ws_device_registry(ws, rest, client):
    """WebSocket config/device_registry/list returns devices with entities."""
    # Create a device and assign an entity
    client.post("/api/devices", json={
        "device_id": "ws_dev_test", "name": "WS Device", "manufacturer": "CTS",
    })
    await rest.set_state("sensor.ws_dev_entity", "99")
    client.post("/api/devices/ws_dev_test/entities/sensor.ws_dev_entity")

    result = await ws.send_command("config/device_registry/list")
    assert result.get("success", False)
    entries = result.get("result", [])
    assert isinstance(entries, list)
    found = next((d for d in entries if d.get("id") == "ws_dev_test"), None)
    assert found is not None
    assert found["name"] == "WS Device"
    assert "sensor.ws_dev_entity" in found.get("entities", [])

    # Cleanup
    client.delete("/api/devices/ws_dev_test/entities/sensor.ws_dev_entity")
    client.delete("/api/devices/ws_dev_test")


# ── WS Label Registry ──────────────────────────────


@pytest.mark.asyncio
async def test_ws_label_registry(ws, rest, client):
    """WebSocket config/label_registry/list returns labels with entities."""
    # Create a label and assign an entity
    client.post("/api/labels", json={
        "label_id": "ws_lbl_test", "name": "WS Label", "color": "#ff0000",
    })
    await rest.set_state("sensor.ws_lbl_entity", "42")
    client.post("/api/labels/ws_lbl_test/entities/sensor.ws_lbl_entity")

    result = await ws.send_command("config/label_registry/list")
    assert result.get("success", False)
    entries = result.get("result", [])
    assert isinstance(entries, list)
    found = next((l for l in entries if l.get("label_id") == "ws_lbl_test"), None)
    assert found is not None
    assert found["name"] == "WS Label"
    assert "sensor.ws_lbl_entity" in found.get("entities", [])

    # Cleanup
    client.delete("/api/labels/ws_lbl_test/entities/sensor.ws_lbl_entity")
    client.delete("/api/labels/ws_lbl_test")


# ── Entity Delete ──────────────────────────────────


@pytest.mark.asyncio
async def test_delete_entity(rest):
    """DELETE /api/states/:entity_id removes the entity."""
    await rest.set_state("sensor.delete_me", "bye")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.delete_me",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state("sensor.delete_me")
    assert state is None


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(rest):
    """DELETE /api/states for nonexistent entity returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.never_existed_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Attribute Round-Trip ─────────────────────────


@pytest.mark.asyncio
async def test_attribute_roundtrip(rest):
    """Setting attributes and reading them back preserves types."""
    attrs = {
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "friendly_name": "Test Energy",
        "precision": 2,
        "values": [1, 2, 3],
    }
    await rest.set_state("sensor.attr_rt", "42.5", attrs)
    state = await rest.get_state("sensor.attr_rt")
    assert state["attributes"]["unit_of_measurement"] == "kWh"
    assert state["attributes"]["precision"] == 2
    assert state["attributes"]["values"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_attribute_update_preserves_state(rest):
    """Updating attributes doesn't change the state value."""
    await rest.set_state("sensor.attr_preserve", "100", {"unit": "W"})
    await rest.set_state("sensor.attr_preserve", "100", {"unit": "kW", "extra": True})
    state = await rest.get_state("sensor.attr_preserve")
    assert state["state"] == "100"
    assert state["attributes"]["unit"] == "kW"
    assert state["attributes"]["extra"] is True


# ── WS Call Service ────────────────────────────────


@pytest.mark.asyncio
async def test_ws_call_service(ws, rest):
    """WebSocket call_service changes entity state."""
    await rest.set_state("light.ws_svc_test", "off")
    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": "light.ws_svc_test"},
    )
    assert result.get("success", False)
    state = await rest.get_state("light.ws_svc_test")
    assert state["state"] == "on"


@pytest.mark.asyncio
async def test_ws_fire_event(ws):
    """WebSocket fire_event succeeds."""
    result = await ws.send_command(
        "fire_event",
        event_type="test_event",
        event_data={"key": "val"},
    )
    assert result.get("success", False)


@pytest.mark.asyncio
async def test_ws_unknown_command(ws):
    """Unknown WS command returns success=false."""
    result = await ws.send_command("totally_fake_command")
    assert result.get("success") is False


# ── Logbook ──────────────────────────────────────


@pytest.mark.asyncio
async def test_logbook_returns_entries(rest):
    """GET /api/logbook returns array with entity_id and state."""
    await rest.set_state("sensor.logbook_test", "abc")
    await asyncio.sleep(0.5)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "entity_id" in data[0]
        assert "state" in data[0]


# ── Health Endpoint ─────────────────────────────


@pytest.mark.asyncio
async def test_health_contains_fields(rest):
    """GET /api/health returns version, entity_count, memory, latency."""
    health = await rest.get_health()
    assert "version" in health
    assert "entity_count" in health
    assert "memory_rss_mb" in health
    assert "latency_avg_us" in health
    assert "startup_ms" in health
    assert health["entity_count"] >= 0


# ── WS Get Config ──────────────────────────────


@pytest.mark.asyncio
async def test_ws_get_config(ws):
    """WebSocket get_config returns location and version."""
    result = await ws.send_command("get_config")
    assert result.get("success", False)
    config = result.get("result", {})
    assert "location_name" in config
    assert "version" in config
    assert "latitude" in config
    assert "unit_system" in config


# ── WS Get Services ────────────────────────────


@pytest.mark.asyncio
async def test_ws_get_services(ws):
    """WebSocket get_services returns domain list."""
    result = await ws.send_command("get_services")
    assert result.get("success", False)
    services = result.get("result", [])
    assert isinstance(services, list)
    domains = [s["domain"] for s in services] if isinstance(services, list) else list(services.keys())
    assert "light" in domains


# ── State Search ───────────────────────────────


def test_state_search(client):
    """GET /api/states/search?q= returns matching entities."""
    client.post("/api/states/sensor.searchable_test", json={"state": "found"})
    r = client.get("/api/states/search", params={"q": "searchable"})
    assert r.status_code == 200
    results = r.json()
    entity_ids = [e["entity_id"] for e in results]
    assert "sensor.searchable_test" in entity_ids


# ── WS Notifications ──────────────────────────


@pytest.mark.asyncio
async def test_ws_get_notifications(ws, client):
    """WebSocket get_notifications returns notification list."""
    # Create a notification first
    client.post("/api/services/persistent_notification/create", json={
        "notification_id": "ws_notif_test",
        "title": "WS Test",
        "message": "Testing WS notifications",
    })
    result = await ws.send_command("get_notifications")
    assert result.get("success", False)
    notifs = result.get("result", [])
    assert isinstance(notifs, list)
    found = [n for n in notifs if n.get("notification_id") == "ws_notif_test"]
    assert len(found) >= 1
    assert found[0]["title"] == "WS Test"

    # Cleanup
    client.post("/api/notifications/ws_notif_test/dismiss")


@pytest.mark.asyncio
async def test_ws_dismiss_notification(ws, client):
    """WebSocket persistent_notification/dismiss removes a notification."""
    client.post("/api/services/persistent_notification/create", json={
        "notification_id": "ws_dismiss_test",
        "title": "Dismiss Me",
        "message": "Should be dismissed via WS",
    })

    result = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id="ws_dismiss_test",
    )
    assert result.get("success", False)

    # Verify it's gone
    r = client.get("/api/notifications")
    notifs = r.json()
    remaining = [n for n in notifs if n.get("notification_id") == "ws_dismiss_test"]
    assert len(remaining) == 0


# ── WS Ping ───────────────────────────────────


@pytest.mark.asyncio
async def test_ws_ping_pong(ws):
    """WebSocket ping returns pong."""
    ok = await ws.ping()
    assert ok


# ── Events List ──────────────────────────────


def test_events_list(client):
    """GET /api/events returns event types list."""
    # Fire a test event
    client.post("/api/events/cts_test_event", json={"key": "val"})
    r = client.get("/api/events")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


# ── Dismiss All Notifications ─────────────────


def test_dismiss_all_notifications(client):
    """POST /api/notifications/dismiss_all clears all notifications."""
    client.post("/api/services/persistent_notification/create", json={
        "notification_id": "dismiss_all_1", "title": "One", "message": "First",
    })
    client.post("/api/services/persistent_notification/create", json={
        "notification_id": "dismiss_all_2", "title": "Two", "message": "Second",
    })
    r = client.post("/api/notifications/dismiss_all")
    assert r.status_code == 200

    r = client.get("/api/notifications")
    assert len(r.json()) == 0


# ── Automation Config ────────────────────────


def test_automation_config_list(client):
    """GET /api/config/automation/config returns automation list."""
    r = client.get("/api/config/automation/config")
    assert r.status_code == 200
    autos = r.json()
    assert isinstance(autos, list)
    if autos:
        assert "id" in autos[0]


def test_automation_yaml_roundtrip(client):
    """GET then PUT automation YAML preserves content."""
    r = client.get("/api/config/automation/yaml")
    assert r.status_code == 200
    yaml_content = r.text

    # PUT back the same content
    r = client.put("/api/config/automation/yaml",
                   content=yaml_content,
                   headers={"Content-Type": "application/x-yaml"})
    assert r.status_code == 200


# ── Scene Config ─────────────────────────────


def test_scene_yaml_roundtrip(client):
    """GET then PUT scene YAML preserves content."""
    r = client.get("/api/config/scene/yaml")
    assert r.status_code == 200
    yaml_content = r.text

    r = client.put("/api/config/scene/yaml",
                   content=yaml_content,
                   headers={"Content-Type": "application/x-yaml"})
    assert r.status_code == 200


# ── Prometheus Metrics ───────────────────────


def test_prometheus_metrics(client):
    """GET /metrics returns Prometheus text format."""
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "marge_" in text or "entity_count" in text


# ── Label CRUD Round-Trip ────────────────────


def test_label_crud_roundtrip(client):
    """Create, list, assign entity, unassign, delete label."""
    # Create
    r = client.post("/api/labels", json={
        "label_id": "cts_crud_label", "name": "CRUD Label", "color": "#123456",
    })
    assert r.status_code in (200, 201)

    # List and verify
    r = client.get("/api/labels")
    labels = r.json()
    found = next((l for l in labels if l["label_id"] == "cts_crud_label"), None)
    assert found is not None
    assert found["name"] == "CRUD Label"

    # Assign entity
    client.post("/api/states/sensor.label_crud_test", json={"state": "1"})
    r = client.post("/api/labels/cts_crud_label/entities/sensor.label_crud_test")
    assert r.status_code == 200

    # Unassign
    r = client.delete("/api/labels/cts_crud_label/entities/sensor.label_crud_test")
    assert r.status_code == 200

    # Delete
    r = client.delete("/api/labels/cts_crud_label")
    assert r.status_code == 200


# ── Device CRUD Round-Trip ───────────────────


def test_device_crud_roundtrip(client):
    """Create, list, assign entity, delete device."""
    r = client.post("/api/devices", json={
        "device_id": "cts_crud_dev", "name": "CRUD Device",
        "manufacturer": "CTS", "model": "TestModel",
    })
    assert r.status_code in (200, 201)

    r = client.get("/api/devices")
    devices = r.json()
    found = next((d for d in devices if d["device_id"] == "cts_crud_dev"), None)
    assert found is not None

    # Assign entity
    client.post("/api/states/sensor.device_crud_test", json={"state": "42"})
    r = client.post("/api/devices/cts_crud_dev/entities/sensor.device_crud_test")
    assert r.status_code == 200

    # Delete device
    r = client.delete("/api/devices/cts_crud_dev")
    assert r.status_code == 200


# ── Search with Domain Filter ─────────────────


def test_state_search_with_domain(client):
    """State search with domain filter limits results."""
    client.post("/api/states/sensor.search_domain_test", json={"state": "10"})
    client.post("/api/states/light.search_domain_test", json={"state": "on"})

    # Search without domain
    r = client.get("/api/states/search", params={"q": "search_domain"})
    all_results = r.json()

    # Search with domain filter
    r = client.get("/api/states/search", params={"q": "search_domain", "domain": "sensor"})
    sensor_results = r.json()
    assert len(sensor_results) <= len(all_results)
    assert all(e["entity_id"].startswith("sensor.") for e in sensor_results)


# ── Statistics Aggregation ──────────────────────────


@pytest.mark.asyncio
async def test_statistics_min_max_accuracy(rest):
    """Statistics min/max accurately reflect written values."""
    entity = "sensor.stats_accuracy"
    values = [5.0, 15.0, 25.0, 10.0, 20.0]
    for v in values:
        await rest.set_state(entity, str(v))
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    bucket = data[0]
    assert bucket["min"] == 5.0
    assert bucket["max"] == 25.0


# ── Entity Lifecycle Edge Cases ─────────────────────


@pytest.mark.asyncio
async def test_set_state_create_and_update(rest):
    """POST /api/states creates and updates entities successfully."""
    unique = f"sensor.lifecycle_{int(time.time() * 1000) % 100000}"
    # Create
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{unique}",
        headers=rest._headers(),
        json={"state": "new", "attributes": {}},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["state"] == "new"
    assert data["entity_id"] == unique

    # Update
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{unique}",
        headers=rest._headers(),
        json={"state": "updated", "attributes": {"key": "val"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "updated"
    assert data["attributes"]["key"] == "val"


# ── Template Edge Cases ─────────────────────────────


@pytest.mark.asyncio
async def test_template_math_operations(rest):
    """Template supports arithmetic operations."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ (10 * 3 + 5) / 7 }}"},
    )
    assert resp.status_code == 200
    assert float(resp.text.strip()) == 5.0


@pytest.mark.asyncio
async def test_template_states_unknown_entity(rest):
    """states() returns 'unknown' for nonexistent entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('sensor.nonexistent_zzz') }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "unknown"


# ── Scene Activation Verifies State ─────────────────


@pytest.mark.asyncio
async def test_scene_activation_sets_entity_states(rest):
    """Activating a scene sets the target entity states."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    if not scenes:
        pytest.skip("No scenes loaded")
    scene = scenes[0]

    # Activate scene
    await rest.call_service("scene", "turn_on", {
        "entity_id": f"scene.{scene['id']}",
    })
    await asyncio.sleep(0.5)

    # Verify at least one entity has the expected state
    for entity_entry in scene.get("entities", []):
        if isinstance(entity_entry, dict):
            eid = entity_entry.get("entity_id")
        else:
            eid = entity_entry
        if eid:
            state = await rest.get_state(eid)
            assert state is not None, f"Entity {eid} from scene should exist"
            break


# ── WS Subscribe + Multiple Events ─────────────────


@pytest.mark.asyncio
async def test_ws_subscribe_multiple_changes(ws, rest):
    """Subscription receives multiple consecutive state changes."""
    await ws.subscribe_events("state_changed")

    for i in range(3):
        await rest.set_state("sensor.ws_multi_test", str(i * 10))
        await asyncio.sleep(0.1)

    events_received = 0
    for _ in range(3):
        try:
            event = await ws.recv_event(timeout=3.0)
            if event.get("type") == "event":
                events_received += 1
        except asyncio.TimeoutError:
            break
    assert events_received >= 2


# ── Cover Services ──────────────────────────────────


@pytest.mark.asyncio
async def test_cover_open_close_cycle(rest):
    """cover.open_cover and cover.close_cover toggle state."""
    await rest.set_state("cover.cts_garage", "closed")
    await rest.call_service("cover", "open_cover", {"entity_id": "cover.cts_garage"})
    state = await rest.get_state("cover.cts_garage")
    assert state["state"] == "open"

    await rest.call_service("cover", "close_cover", {"entity_id": "cover.cts_garage"})
    state = await rest.get_state("cover.cts_garage")
    assert state["state"] == "closed"


# ── Concurrent WebSocket Commands ───────────────────


@pytest.mark.asyncio
async def test_ws_rapid_commands(ws):
    """WS handles rapid sequential commands without errors."""
    commands = ["get_config", "get_states", "get_services", "get_notifications"]
    for cmd in commands:
        result = await ws.send_command(cmd)
        assert result.get("success", False), f"Command {cmd} failed"


# ── Area Duplicate Prevention ───────────────────────


@pytest.mark.asyncio
async def test_area_duplicate_entity_assignment(rest):
    """Assigning same entity to area twice is idempotent."""
    await rest.set_state("sensor.dup_area_test", "10")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "dup_test_room", "name": "Dup Room"},
    )

    # Assign twice
    for _ in range(2):
        resp = await rest.client.post(
            f"{rest.base_url}/api/areas/dup_test_room/entities/sensor.dup_area_test",
            headers=rest._headers(),
        )
        assert resp.status_code == 200

    # Verify entity appears only once
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    areas = resp.json()
    room = next((a for a in areas if a["area_id"] == "dup_test_room"), None)
    assert room is not None
    count = room["entities"].count("sensor.dup_area_test")
    assert count == 1

    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/areas/dup_test_room",
        headers=rest._headers(),
    )


# ── History Ordered ─────────────────────────────────


@pytest.mark.asyncio
async def test_history_entries_ordered_by_time(rest):
    """History entries are returned in chronological order."""
    entity = "sensor.history_order"
    for val in ["a", "b", "c"]:
        await rest.set_state(entity, val)
        await asyncio.sleep(0.3)
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    timestamps = [e["last_changed"] for e in data]
    assert timestamps == sorted(timestamps)


# ── Health & Metrics Endpoint ──────────────────────


@pytest.mark.asyncio
async def test_health_ws_connections_field(rest):
    """Health endpoint includes ws_connections field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "ws_connections" in data
    assert isinstance(data["ws_connections"], int)
    assert data["ws_connections"] >= 0


@pytest.mark.asyncio
async def test_health_all_fields_present(rest):
    """Health endpoint returns all expected fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    required = [
        "status", "version", "entity_count", "memory_rss_mb",
        "uptime_seconds", "startup_ms", "state_changes",
        "latency_avg_us", "latency_max_us", "ws_connections",
    ]
    for field in required:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(rest):
    """GET /metrics returns Prometheus-format text."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "marge_entity_count" in text
    assert "marge_uptime_seconds" in text
    assert "marge_ws_connections" in text
    assert "marge_memory_rss_bytes" in text


# ── Search API ─────────────────────────────────────


@pytest.mark.asyncio
async def test_search_by_domain_async(rest):
    """GET /api/states/search?domain=light filters by domain (async)."""
    await rest.set_state("light.search_test1", "on")
    await rest.set_state("sensor.search_test1", "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert all(e["entity_id"].startswith("light.") for e in results)


@pytest.mark.asyncio
async def test_search_by_state_async(rest):
    """GET /api/states/search?state=on filters by state value (async)."""
    await rest.set_state("switch.search_on", "on")
    await rest.set_state("switch.search_off", "off")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?state=on",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert all(e["state"] == "on" for e in results)


@pytest.mark.asyncio
async def test_search_by_text_query(rest):
    """GET /api/states/search?q=text matches entity_id."""
    await rest.set_state("sensor.unique_search_xyz", "99")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=unique_search_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any(e["entity_id"] == "sensor.unique_search_xyz" for e in results)


# ── Label CRUD ─────────────────────────────────────


@pytest.mark.asyncio
async def test_label_crud_async(rest):
    """Labels can be created, listed, and deleted (async)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": "cts_test_label", "name": "CTS Label", "color": "#ff0000"},
    )
    assert resp.status_code == 200

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    labels = resp.json()
    assert any(l["label_id"] == "cts_test_label" for l in labels)

    resp = await rest.client.delete(
        f"{rest.base_url}/api/labels/cts_test_label",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_label_entity_assign_unassign(rest):
    """Entities can be labeled and unlabeled."""
    await rest.set_state("sensor.label_test", "42")
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": "cts_assign_label", "name": "Assign Label", "color": "#00ff00"},
    )

    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/cts_assign_label/entities/sensor.label_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label = next(l for l in resp.json() if l["label_id"] == "cts_assign_label")
    assert "sensor.label_test" in label["entities"]

    # Unassign
    resp = await rest.client.delete(
        f"{rest.base_url}/api/labels/cts_assign_label/entities/sensor.label_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Cleanup
    await rest.client.delete(
        f"{rest.base_url}/api/labels/cts_assign_label",
        headers=rest._headers(),
    )


# ── Service Listing ────────────────────────────────


@pytest.mark.asyncio
async def test_services_list_includes_light(rest):
    """GET /api/services includes light domain with turn_on."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    light = next((d for d in data if d["domain"] == "light"), None)
    assert light is not None
    assert "turn_on" in light["services"]


# ── Event Types ────────────────────────────────────


@pytest.mark.asyncio
async def test_events_list_includes_state_changed(rest):
    """GET /api/events returns list including state_changed."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    events = [e["event"] for e in data]
    assert "state_changed" in events


# ── Media Player Services ──────────────────────────


@pytest.mark.asyncio
async def test_media_player_play_pause(rest):
    """media_player.media_play and media_pause toggle state."""
    await rest.set_state("media_player.speaker", "paused")
    await rest.call_service("media_player", "media_play", {"entity_id": "media_player.speaker"})
    state = await rest.get_state("media_player.speaker")
    assert state["state"] == "playing"

    await rest.call_service("media_player", "media_pause", {"entity_id": "media_player.speaker"})
    state = await rest.get_state("media_player.speaker")
    assert state["state"] == "paused"


@pytest.mark.asyncio
async def test_media_player_volume_set(rest):
    """media_player.volume_set updates volume_level attribute."""
    await rest.set_state("media_player.tv", "on")
    await rest.call_service("media_player", "volume_set", {"entity_id": "media_player.tv", "volume_level": 0.65})
    state = await rest.get_state("media_player.tv")
    assert state["attributes"]["volume_level"] == 0.65


@pytest.mark.asyncio
async def test_media_player_turn_on_off(rest):
    """media_player.turn_on and turn_off toggle power."""
    await rest.set_state("media_player.amp", "off")
    await rest.call_service("media_player", "turn_on", {"entity_id": "media_player.amp"})
    state = await rest.get_state("media_player.amp")
    assert state["state"] == "on"

    await rest.call_service("media_player", "turn_off", {"entity_id": "media_player.amp"})
    state = await rest.get_state("media_player.amp")
    assert state["state"] == "off"


# ── Vacuum Services ────────────────────────────────


@pytest.mark.asyncio
async def test_vacuum_start_stop(rest):
    """vacuum.start and stop control cleaning state."""
    await rest.set_state("vacuum.roborock", "idle")
    await rest.call_service("vacuum", "start", {"entity_id": "vacuum.roborock"})
    state = await rest.get_state("vacuum.roborock")
    assert state["state"] == "cleaning"

    await rest.call_service("vacuum", "stop", {"entity_id": "vacuum.roborock"})
    state = await rest.get_state("vacuum.roborock")
    assert state["state"] == "idle"


@pytest.mark.asyncio
async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base sets state to returning."""
    await rest.set_state("vacuum.dyson", "cleaning")
    await rest.call_service("vacuum", "return_to_base", {"entity_id": "vacuum.dyson"})
    state = await rest.get_state("vacuum.dyson")
    assert state["state"] == "returning"


# ── Number Services ────────────────────────────────


@pytest.mark.asyncio
async def test_number_set_value(rest):
    """number.set_value sets the state to the numeric value."""
    await rest.set_state("number.brightness", "50")
    await rest.call_service("number", "set_value", {"entity_id": "number.brightness", "value": 75})
    state = await rest.get_state("number.brightness")
    assert state["state"] == "75"


# ── Select Services ────────────────────────────────


@pytest.mark.asyncio
async def test_select_option(rest):
    """select.select_option sets the selected option as state."""
    await rest.set_state("select.color_mode", "warm")
    await rest.call_service("select", "select_option", {"entity_id": "select.color_mode", "option": "cool"})
    state = await rest.get_state("select.color_mode")
    assert state["state"] == "cool"


# ── Siren Services ─────────────────────────────────


@pytest.mark.asyncio
async def test_siren_on_off(rest):
    """siren.turn_on and turn_off toggle siren state."""
    await rest.set_state("siren.alarm", "off")
    await rest.call_service("siren", "turn_on", {"entity_id": "siren.alarm"})
    state = await rest.get_state("siren.alarm")
    assert state["state"] == "on"

    await rest.call_service("siren", "turn_off", {"entity_id": "siren.alarm"})
    state = await rest.get_state("siren.alarm")
    assert state["state"] == "off"


# ── Valve Services ─────────────────────────────────


@pytest.mark.asyncio
async def test_valve_open_close(rest):
    """valve.open_valve and close_valve toggle valve state."""
    await rest.set_state("valve.water_main", "closed")
    await rest.call_service("valve", "open_valve", {"entity_id": "valve.water_main"})
    state = await rest.get_state("valve.water_main")
    assert state["state"] == "open"

    await rest.call_service("valve", "close_valve", {"entity_id": "valve.water_main"})
    state = await rest.get_state("valve.water_main")
    assert state["state"] == "closed"


# ── Edge Cases & Robustness ─────────────────────────────


@pytest.mark.asyncio
async def test_set_state_preserves_last_changed_on_same_value(rest):
    """Setting the same state value should update last_updated but not last_changed."""
    await rest.set_state("sensor.stable", "42")
    s1 = await rest.get_state("sensor.stable")
    changed1 = s1["last_changed"]

    await asyncio.sleep(0.05)
    await rest.set_state("sensor.stable", "42")
    s2 = await rest.get_state("sensor.stable")
    # last_changed should be the same (state didn't change)
    assert s2["last_changed"] == changed1
    # last_updated should be different
    assert s2["last_updated"] >= changed1


@pytest.mark.asyncio
async def test_set_state_updates_last_changed_on_new_value(rest):
    """Setting a different state value should update last_changed."""
    await rest.set_state("sensor.changing", "10")
    s1 = await rest.get_state("sensor.changing")
    changed1 = s1["last_changed"]

    await asyncio.sleep(0.05)
    await rest.set_state("sensor.changing", "20")
    s2 = await rest.get_state("sensor.changing")
    assert s2["last_changed"] > changed1


@pytest.mark.asyncio
async def test_entity_attributes_support_nested_objects(rest):
    """Attributes can contain nested objects and arrays."""
    attrs = {
        "nested": {"a": 1, "b": [2, 3]},
        "list": [1, "two", True],
        "null_val": None,
    }
    await rest.set_state("sensor.complex_attrs", "ok", attributes=attrs)
    s = await rest.get_state("sensor.complex_attrs")
    assert s["attributes"]["nested"]["a"] == 1
    assert s["attributes"]["nested"]["b"] == [2, 3]
    assert s["attributes"]["list"] == [1, "two", True]
    assert s["attributes"]["null_val"] is None


@pytest.mark.asyncio
async def test_service_call_returns_affected_entities(rest):
    """Service calls should return data about affected entity states."""
    await rest.set_state("light.svc_test", "off")
    result = await rest.call_service("light", "turn_on", {"entity_id": "light.svc_test"})
    # Marge returns {changed_states: [...]} or a list
    if isinstance(result, dict):
        states = result.get("changed_states", [])
    else:
        states = result
    assert isinstance(states, list)
    assert len(states) >= 1
    entity_ids = [e["entity_id"] for e in states]
    assert "light.svc_test" in entity_ids


@pytest.mark.asyncio
async def test_get_states_returns_all_entities(rest):
    """GET /api/states returns all known entities."""
    await rest.set_state("sensor.all_test_1", "a")
    await rest.set_state("sensor.all_test_2", "b")
    states = await rest.get_states()
    entity_ids = [s["entity_id"] for s in states]
    assert "sensor.all_test_1" in entity_ids
    assert "sensor.all_test_2" in entity_ids


@pytest.mark.asyncio
async def test_input_boolean_on_off_cycle(rest):
    """input_boolean supports turn_on, turn_off, toggle in sequence."""
    await rest.set_state("input_boolean.cycle_test", "off")
    await rest.call_service("input_boolean", "turn_on", {"entity_id": "input_boolean.cycle_test"})
    s = await rest.get_state("input_boolean.cycle_test")
    assert s["state"] == "on"

    await rest.call_service("input_boolean", "turn_off", {"entity_id": "input_boolean.cycle_test"})
    s = await rest.get_state("input_boolean.cycle_test")
    assert s["state"] == "off"

    await rest.call_service("input_boolean", "toggle", {"entity_id": "input_boolean.cycle_test"})
    s = await rest.get_state("input_boolean.cycle_test")
    assert s["state"] == "on"


@pytest.mark.asyncio
async def test_cover_position_tracking(rest):
    """Setting cover position updates entity attributes."""
    await rest.set_state("cover.pos_test", "open", attributes={"current_position": 100})
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": "cover.pos_test",
        "position": 50,
    })
    s = await rest.get_state("cover.pos_test")
    assert s["attributes"]["current_position"] == 50


@pytest.mark.asyncio
async def test_fan_percentage_tracking(rest):
    """Setting fan percentage updates entity attributes."""
    await rest.set_state("fan.pct_test", "on", attributes={"percentage": 50})
    await rest.call_service("fan", "set_percentage", {
        "entity_id": "fan.pct_test",
        "percentage": 75,
    })
    s = await rest.get_state("fan.pct_test")
    assert s["attributes"]["percentage"] == 75


@pytest.mark.asyncio
async def test_fire_event_with_data(rest):
    """Firing a custom event with data returns success."""
    result = await rest.fire_event("test_custom_event", data={
        "source": "cts",
        "value": 42,
    })
    assert result.get("message", "").lower().startswith("event")


@pytest.mark.asyncio
async def test_backup_contains_state_db(client):
    """Backup tar.gz should contain the state database."""
    resp = client.get("/api/backup")
    assert resp.status_code == 200
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        # Should contain at least the DB file
        assert any("state" in n.lower() or "marge" in n.lower() or "db" in n.lower()
                    or "automations" in n.lower() for n in names), \
            f"Backup contents: {names}"


@pytest.mark.asyncio
async def test_ws_subscribe_event_has_entity_id(ws, rest):
    """WS state_changed events should include entity_id in event data."""
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_eid_test", "hello")
    event = await ws.recv_event(timeout=5)
    assert event["type"] == "event"
    data = event["event"]["data"]
    assert data["entity_id"] == "sensor.ws_eid_test"
    assert data["new_state"]["state"] == "hello"


# ── Input Helpers ────────────────────────────────────────


@pytest.mark.asyncio
async def test_input_text_set_value_service(rest):
    """input_text.set_value service updates entity state."""
    await rest.set_state("input_text.greeting", "hello")
    await rest.call_service("input_text", "set_value", {
        "entity_id": "input_text.greeting",
        "value": "goodbye",
    })
    s = await rest.get_state("input_text.greeting")
    assert s["state"] == "goodbye"


@pytest.mark.asyncio
async def test_input_select_select_option_service(rest):
    """input_select.select_option updates entity state."""
    await rest.set_state("input_select.mode", "auto", attributes={"options": ["auto", "manual", "off"]})
    await rest.call_service("input_select", "select_option", {
        "entity_id": "input_select.mode",
        "option": "manual",
    })
    s = await rest.get_state("input_select.mode")
    assert s["state"] == "manual"


# ── Automation Services ──────────────────────────────────


@pytest.mark.asyncio
async def test_automation_turn_on_and_off_services(rest):
    """automation.turn_on and turn_off toggle the automation entity state."""
    await rest.set_state("automation.test_svc", "on")
    await rest.call_service("automation", "turn_off", {"entity_id": "automation.test_svc"})
    s = await rest.get_state("automation.test_svc")
    assert s["state"] == "off"

    await rest.call_service("automation", "turn_on", {"entity_id": "automation.test_svc"})
    s = await rest.get_state("automation.test_svc")
    assert s["state"] == "on"


@pytest.mark.asyncio
async def test_scene_turn_on_service(rest):
    """scene.turn_on activates a scene entity."""
    await rest.set_state("scene.test_activate", "scening")
    result = await rest.call_service("scene", "turn_on", {"entity_id": "scene.test_activate"})
    # Service should succeed (returned data)
    assert result is not None


# ── Template Rendering ───────────────────────────────────


@pytest.mark.asyncio
async def test_template_boolean_comparison(rest):
    """Template engine handles boolean comparisons."""
    await rest.set_state("sensor.temp", "75.5")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('sensor.temp') | float > 70 }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() in ("true", "True")


@pytest.mark.asyncio
async def test_template_default_filter(rest):
    """Template default filter provides fallback for missing state."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('sensor.nonexistent') | default('N/A') }}"},
    )
    assert resp.status_code == 200
    text = resp.text.strip()
    assert text in ("N/A", "unknown", "unavailable")


# ── WebSocket Edge Cases ─────────────────────────────────


@pytest.mark.asyncio
async def test_ws_get_states_includes_attributes(ws, rest):
    """WS get_states result includes entity attributes."""
    await rest.set_state("sensor.ws_attr_test", "42", attributes={"unit": "deg"})
    states = await ws.get_states()
    entity = next((s for s in states if s["entity_id"] == "sensor.ws_attr_test"), None)
    assert entity is not None
    assert entity["state"] == "42"
    assert entity["attributes"]["unit"] == "deg"


@pytest.mark.asyncio
async def test_ws_multiple_subscribes(ws, rest):
    """Multiple WS subscriptions receive the same events."""
    sub1 = await ws.subscribe_events("state_changed")
    sub2 = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.multi_sub", "value")
    event1 = await ws.recv_event(timeout=5)
    event2 = await ws.recv_event(timeout=5)
    assert event1["type"] == "event"
    assert event2["type"] == "event"


# ── Search Edge Cases ────────────────────────────────────


@pytest.mark.asyncio
async def test_search_by_area(rest):
    """Search by area_id returns entities assigned to that area."""
    # Create area and assign entity
    area_resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "search_area", "name": "Search Area"},
    )
    await rest.set_state("sensor.in_search_area", "42")
    await rest.client.post(
        f"{rest.base_url}/api/areas/search_area/entities/sensor.in_search_area",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area=search_area",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    entity_ids = [r["entity_id"] for r in results]
    assert "sensor.in_search_area" in entity_ids


@pytest.mark.asyncio
async def test_logbook_entries_have_entity_id_and_state(rest):
    """Logbook entries should have entity_id, state, and when fields."""
    await rest.set_state("sensor.logbook_field_test", "first")
    await rest.set_state("sensor.logbook_field_test", "second")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) > 0
    entry = entries[-1]
    assert "entity_id" in entry
    assert "state" in entry
    assert "when" in entry
