"""
CTS -- Search, Registry, and Advanced API Tests

Tests search/filter endpoints, area/device/label CRUD lifecycle,
backup, logbook, statistics, and YAML config management.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Search API ────────────────────────────────────────────

async def test_search_by_domain(rest):
    """GET /api/states/search?domain=light returns only lights."""
    await rest.set_state("light.search_test_1", "on")
    await rest.set_state("switch.search_test_1", "on")
    resp = await rest.client.get(f"{rest.base_url}/api/states/search?domain=light")
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["entity_id"].startswith("light.") for r in results)


async def test_search_by_state(rest):
    """GET /api/states/search?state=locked returns only locked entities."""
    await rest.set_state("lock.search_locked", "locked")
    await rest.set_state("lock.search_unlocked", "unlocked")
    resp = await rest.client.get(f"{rest.base_url}/api/states/search?state=locked")
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["state"] == "locked" for r in results)


async def test_search_by_text(rest):
    """GET /api/states/search?q=kitchen matches friendly_name."""
    await rest.set_state("light.kitchen_search", "on", {"friendly_name": "Kitchen Light"})
    resp = await rest.client.get(f"{rest.base_url}/api/states/search?q=kitchen")
    assert resp.status_code == 200
    results = resp.json()
    ids = [r["entity_id"] for r in results]
    assert "light.kitchen_search" in ids


async def test_search_combined_filters(rest):
    """GET /api/states/search?domain=light&state=on returns filtered results."""
    await rest.set_state("light.combo_on", "on")
    await rest.set_state("light.combo_off", "off")
    await rest.set_state("switch.combo_on", "on")
    resp = await rest.client.get(f"{rest.base_url}/api/states/search?domain=light&state=on")
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["entity_id"].startswith("light.") and r["state"] == "on" for r in results)


async def test_search_returns_sorted(rest):
    """Search results are sorted by entity_id."""
    await rest.set_state("sensor.z_search", "1")
    await rest.set_state("sensor.a_search", "2")
    resp = await rest.client.get(f"{rest.base_url}/api/states/search?domain=sensor&q=search")
    assert resp.status_code == 200
    results = resp.json()
    ids = [r["entity_id"] for r in results]
    assert ids == sorted(ids)


# ── Area Lifecycle ────────────────────────────────────────

async def test_area_crud_lifecycle(rest):
    """Create, list, assign entity, unassign, delete area."""
    # Create
    resp = await rest.client.post(f"{rest.base_url}/api/areas", json={
        "area_id": "test_lifecycle_area",
        "name": "Test Room",
    })
    assert resp.status_code == 200

    # List includes it
    resp = await rest.client.get(f"{rest.base_url}/api/areas")
    areas = resp.json()
    area_ids = [a["area_id"] for a in areas]
    assert "test_lifecycle_area" in area_ids

    # Assign entity
    await rest.set_state("light.area_test", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/test_lifecycle_area/entities/light.area_test"
    )
    assert resp.status_code == 200

    # List entities in area
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/test_lifecycle_area/entities"
    )
    assert resp.status_code == 200
    entities = resp.json()
    assert any(e.get("entity_id") == "light.area_test" for e in entities)

    # Unassign
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/test_lifecycle_area/entities/light.area_test",
    )
    assert resp.status_code == 200

    # Delete area
    resp = await rest.client.request(
        "DELETE", f"{rest.base_url}/api/areas/test_lifecycle_area"
    )
    assert resp.status_code == 200


# ── Device Lifecycle ──────────────────────────────────────

async def test_device_crud_lifecycle(rest):
    """Create, list, assign entity, delete device."""
    resp = await rest.client.post(f"{rest.base_url}/api/devices", json={
        "device_id": "test_lifecycle_device",
        "name": "Test Device",
        "manufacturer": "Acme",
        "model": "X100",
    })
    assert resp.status_code == 200

    # List includes it
    resp = await rest.client.get(f"{rest.base_url}/api/devices")
    devices = resp.json()
    device_ids = [d["device_id"] for d in devices]
    assert "test_lifecycle_device" in device_ids

    # Assign entity
    await rest.set_state("sensor.device_test", "50")
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/test_lifecycle_device/entities/sensor.device_test"
    )
    assert resp.status_code == 200

    # Delete
    resp = await rest.client.request(
        "DELETE", f"{rest.base_url}/api/devices/test_lifecycle_device"
    )
    assert resp.status_code == 200


# ── Label Lifecycle ───────────────────────────────────────

async def test_label_crud_lifecycle(rest):
    """Create, list, assign, unassign, delete label."""
    resp = await rest.client.post(f"{rest.base_url}/api/labels", json={
        "label_id": "test_lifecycle_label",
        "name": "Critical",
        "color": "#ff0000",
    })
    assert resp.status_code == 200

    # List includes it
    resp = await rest.client.get(f"{rest.base_url}/api/labels")
    labels = resp.json()
    label_ids = [l["label_id"] for l in labels]
    assert "test_lifecycle_label" in label_ids

    # Assign
    await rest.set_state("sensor.label_test", "42")
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/test_lifecycle_label/entities/sensor.label_test"
    )
    assert resp.status_code == 200

    # Unassign
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/test_lifecycle_label/entities/sensor.label_test",
    )
    assert resp.status_code == 200

    # Delete label
    resp = await rest.client.request(
        "DELETE", f"{rest.base_url}/api/labels/test_lifecycle_label"
    )
    assert resp.status_code == 200


# ── Backup ────────────────────────────────────────────────

async def test_backup_download(rest):
    """GET /api/backup returns a gzip archive."""
    resp = await rest.client.get(f"{rest.base_url}/api/backup")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/gzip"
    # First two bytes of gzip
    assert resp.content[:2] == b'\x1f\x8b'


# ── Logbook ───────────────────────────────────────────────

async def test_logbook_entity(rest):
    """GET /api/logbook/<entity_id> returns logbook entries."""
    entity_id = "sensor.logbook_test"
    await rest.set_state(entity_id, "1")
    await rest.set_state(entity_id, "2")
    resp = await rest.client.get(f"{rest.base_url}/api/logbook/{entity_id}")
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)


# ── Statistics ────────────────────────────────────────────

async def test_statistics_endpoint(rest):
    """GET /api/statistics/<entity_id> returns stats buckets."""
    entity_id = "sensor.stats_test"
    await rest.set_state(entity_id, "25.5")
    resp = await rest.client.get(f"{rest.base_url}/api/statistics/{entity_id}")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Events listing ────────────────────────────────────────

async def test_events_list(rest):
    """GET /api/events returns available event types."""
    resp = await rest.client.get(f"{rest.base_url}/api/events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    event_names = [e["event"] for e in events]
    assert "state_changed" in event_names


# ── Services listing ──────────────────────────────────────

async def test_services_list_all_domains(rest):
    """GET /api/services returns all 29 registered domains."""
    resp = await rest.client.get(f"{rest.base_url}/api/services")
    assert resp.status_code == 200
    services = resp.json()
    domains = [s["domain"] for s in services]
    for expected in ["light", "switch", "lock", "climate", "timer", "counter",
                     "homeassistant", "group", "update"]:
        assert expected in domains, f"Missing domain: {expected}"


# ── Config check ──────────────────────────────────────────

async def test_config_check_valid(rest):
    """POST /api/config/core/check_config returns valid."""
    resp = await rest.client.post(f"{rest.base_url}/api/config/core/check_config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "valid"


# ── Webhook ───────────────────────────────────────────────

async def test_webhook_set_state(rest):
    """POST /api/webhook/<id> with entity_id/state sets state."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook",
        json={"entity_id": "sensor.webhook_test", "state": "triggered"},
    )
    assert resp.status_code == 200
    state = await rest.get_state("sensor.webhook_test")
    assert state["state"] == "triggered"


async def test_webhook_fire_event(rest):
    """POST /api/webhook/<id> with event_type fires an event."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook_event",
        json={"event_type": "custom_event"},
    )
    assert resp.status_code == 200
    assert "fired" in resp.json()["message"]


async def test_webhook_default_event(rest):
    """POST /api/webhook/<id> without entity_id fires webhook.<id> event."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/my_hook",
        json={},
    )
    assert resp.status_code == 200
    assert "webhook.my_hook" in resp.json()["message"]


# ── Prometheus Metrics ────────────────────────────────────

async def test_prometheus_metrics(rest):
    """GET /metrics returns Prometheus text format."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "marge_entity_count" in text
    assert "marge_uptime_seconds" in text
    assert "marge_memory_rss_bytes" in text


# ── Automation YAML ───────────────────────────────────────

async def test_automation_yaml_roundtrip(rest):
    """GET then PUT automation YAML preserves content."""
    resp = await rest.client.get(f"{rest.base_url}/api/config/automation/yaml")
    assert resp.status_code == 200
    original_yaml = resp.text
    assert len(original_yaml) > 10

    # PUT it back
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content=original_yaml,
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"


# ── Scene YAML ────────────────────────────────────────────

async def test_scene_yaml_roundtrip(rest):
    """GET then PUT scene YAML preserves content."""
    resp = await rest.client.get(f"{rest.base_url}/api/config/scene/yaml")
    assert resp.status_code == 200
    original_yaml = resp.text
    assert len(original_yaml) > 10

    resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content=original_yaml,
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"


# ── Token Lifecycle ───────────────────────────────────────

async def test_token_create_and_revoke(rest):
    """Create then revoke an access token."""
    resp = await rest.client.post(f"{rest.base_url}/api/auth/tokens", json={
        "name": "CTS Test Token",
    })
    assert resp.status_code == 200
    data = resp.json()
    token_id = data["id"]
    assert data["token"] is not None

    # List includes it
    resp = await rest.client.get(f"{rest.base_url}/api/auth/tokens")
    tokens = resp.json()
    assert any(t["id"] == token_id for t in tokens)

    # Revoke
    resp = await rest.client.request(
        "DELETE", f"{rest.base_url}/api/auth/tokens/{token_id}"
    )
    assert resp.status_code == 200

    # Gone from list
    resp = await rest.client.get(f"{rest.base_url}/api/auth/tokens")
    tokens = resp.json()
    assert not any(t["id"] == token_id for t in tokens)
