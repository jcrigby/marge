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
        assert len(concurrent_ids) == 20


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
