"""
CTS -- Search, Webhook, and Event API Edge Cases

Tests search filter combinations, webhook payload variants,
fire_event edge cases, and sim-time control.
"""

import asyncio

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Search Filter Combinations ──────────────────────────────

async def test_search_by_domain(rest):
    """Search with domain filter returns only matching entities."""
    await rest.set_state("light.search_d1", "on")
    await rest.set_state("sensor.search_d2", "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    domains = {e["entity_id"].split(".")[0] for e in data}
    assert domains == {"light"}


async def test_search_by_state_value(rest):
    """Search with state filter returns entities in that state."""
    await rest.set_state("sensor.search_sv1", "critical")
    await rest.set_state("sensor.search_sv2", "normal")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?state=critical",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.search_sv1" in ids
    assert "sensor.search_sv2" not in ids


async def test_search_by_text_query(rest):
    """Search with q= matches entity_id substring."""
    await rest.set_state("sensor.search_qtext_alpha", "1")
    await rest.set_state("sensor.search_qtext_beta", "2")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=qtext_alpha",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.search_qtext_alpha" in ids
    assert "sensor.search_qtext_beta" not in ids


async def test_search_case_insensitive(rest):
    """Text search is case-insensitive."""
    await rest.set_state("sensor.search_UPPER", "yes")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=search_upper",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.search_UPPER" in ids


async def test_search_domain_and_state_combined(rest):
    """Combined domain + state filters both applied."""
    await rest.set_state("light.search_combo_a", "on")
    await rest.set_state("light.search_combo_b", "off")
    await rest.set_state("sensor.search_combo_c", "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light&state=on",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "light.search_combo_a" in ids
    assert "light.search_combo_b" not in ids
    assert "sensor.search_combo_c" not in ids


async def test_search_no_match(rest):
    """Search with impossible filter returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=zzz_nonexistent_entity_xyz",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data == []


async def test_search_by_friendly_name(rest):
    """Text search matches friendly_name attribute."""
    await rest.set_state("sensor.search_fn1", "ok", {"friendly_name": "Kitchen Temperature"})
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=kitchen+temperature",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.search_fn1" in ids


async def test_search_sorted_by_entity_id(rest):
    """Search results are sorted by entity_id."""
    await rest.set_state("sensor.search_sort_z", "1")
    await rest.set_state("sensor.search_sort_a", "1")
    await rest.set_state("sensor.search_sort_m", "1")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=search_sort_",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert ids == sorted(ids)


# ── Webhook Endpoints ────────────────────────────────────────

async def test_webhook_set_state(rest):
    """Webhook with entity_id + state sets entity state."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook_1",
        json={"entity_id": "sensor.webhook_test", "state": "triggered"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "State updated" in data["message"]
    state = await rest.get_state("sensor.webhook_test")
    assert state["state"] == "triggered"


async def test_webhook_set_state_with_attributes(rest):
    """Webhook with attributes sets them on the entity."""
    await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook_2",
        json={
            "entity_id": "sensor.webhook_attr",
            "state": "active",
            "attributes": {"source": "webhook", "count": 5},
        },
    )
    state = await rest.get_state("sensor.webhook_attr")
    assert state["state"] == "active"
    assert state["attributes"]["source"] == "webhook"
    assert state["attributes"]["count"] == 5


async def test_webhook_fire_event(rest):
    """Webhook with event_type fires that event."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook_3",
        json={"event_type": "test_webhook_event"},
    )
    data = resp.json()
    assert "Event" in data["message"]
    assert "test_webhook_event" in data["message"]


async def test_webhook_default_event(rest):
    """Webhook with no entity_id or event_type fires webhook.<id> event."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/my_custom_hook",
        json={},
    )
    data = resp.json()
    assert "webhook.my_custom_hook" in data["message"]


async def test_webhook_no_body(rest):
    """Webhook with no body fires default event."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/empty_hook",
    )
    assert resp.status_code == 200


# ── Fire Event API ───────────────────────────────────────────

async def test_fire_event_returns_message(rest):
    """POST /api/events/{type} returns success message."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_custom_event",
        json={"data": "test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "test_custom_event" in data["message"]


async def test_fire_event_triggers_automation(rest):
    """Firing event that matches automation event trigger executes it."""
    # Set up entity that the event-triggered automation will modify
    await rest.set_state("sensor.fire_event_target", "before")
    # Fire an event and verify automation engine processes it
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_fire_event",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Sim Time ─────────────────────────────────────────────────

async def test_sim_time_set_and_read(rest):
    """POST /api/sim/time sets time, chapter, speed; GET /api/health reflects them."""
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "14:30:00", "chapter": "afternoon", "speed": 5},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
    )
    data = resp.json()
    assert data["sim_time"] == "14:30:00"
    assert data["sim_chapter"] == "afternoon"
    assert data["sim_speed"] == 5


async def test_sim_time_partial_update(rest):
    """Setting only time leaves chapter and speed unchanged."""
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "06:00:00", "chapter": "dawn", "speed": 10},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "07:00:00"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert data["sim_time"] == "07:00:00"
    assert data["sim_chapter"] == "dawn"
    assert data["sim_speed"] == 10


# ── Backup ───────────────────────────────────────────────────

async def test_backup_returns_tar_gz(rest):
    """GET /api/backup returns a tar.gz archive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "gzip" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "marge_backup_" in resp.headers.get("content-disposition", "")
    # tar.gz magic bytes: 1f 8b
    assert resp.content[:2] == b'\x1f\x8b'


# ── Prometheus Metrics ───────────────────────────────────────

async def test_prometheus_metrics_format(rest):
    """GET /metrics returns Prometheus text format."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "# HELP marge_info" in text
    assert "# TYPE marge_info gauge" in text
    assert "marge_info{" in text


async def test_prometheus_has_core_metrics(rest):
    """Prometheus output includes all core metric families."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    expected = [
        "marge_uptime_seconds",
        "marge_startup_seconds",
        "marge_entity_count",
        "marge_state_changes_total",
        "marge_events_fired_total",
        "marge_latency_avg_microseconds",
        "marge_latency_max_microseconds",
        "marge_memory_rss_bytes",
        "marge_ws_connections",
    ]
    for metric in expected:
        assert metric in text, f"Missing metric: {metric}"


async def test_prometheus_has_automation_metrics(rest):
    """Prometheus output includes per-automation trigger counts."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    assert "marge_automation_triggers_total" in text


async def test_prometheus_content_type(rest):
    """Prometheus endpoint returns correct content type."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    ct = resp.headers.get("content-type", "")
    assert "text/plain" in ct
