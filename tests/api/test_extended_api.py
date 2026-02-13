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
    entity = "sensor.logbook_test"
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
