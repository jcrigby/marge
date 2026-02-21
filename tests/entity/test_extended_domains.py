"""
CTS -- Extended Domain Service Tests

Tests services for camera, device_tracker, and service listing.
"""

import pytest

pytestmark = pytest.mark.asyncio


# -- Camera --

@pytest.mark.marge_only
async def test_camera_turn_on(rest):
    """camera.turn_on sets state to streaming."""
    await rest.set_state("camera.front_door", "idle")
    await rest.call_service("camera", "turn_on", {
        "entity_id": "camera.front_door",
    })
    state = await rest.get_state("camera.front_door")
    assert state["state"] == "streaming"


@pytest.mark.marge_only
async def test_camera_turn_off(rest):
    """camera.turn_off sets state to idle."""
    await rest.set_state("camera.front_door", "streaming")
    await rest.call_service("camera", "turn_off", {
        "entity_id": "camera.front_door",
    })
    state = await rest.get_state("camera.front_door")
    assert state["state"] == "idle"


# -- Device Tracker --

@pytest.mark.marge_only
async def test_device_tracker_see(rest):
    """device_tracker.see sets location state."""
    await rest.set_state("device_tracker.phone", "not_home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": "device_tracker.phone",
        "location_name": "home",
    })
    state = await rest.get_state("device_tracker.phone")
    assert state["state"] == "home"
    assert state["attributes"]["location_name"] == "home"


# -- Persistent Notification Service Listing --

async def test_services_include_persistent_notification(rest):
    """GET /api/services includes dismiss and dismiss_all for persistent_notification."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    pn = next(s for s in services if s["domain"] == "persistent_notification")
    svc_names = list(pn["services"].keys())
    assert "create" in svc_names
    assert "dismiss" in svc_names
    assert "dismiss_all" in svc_names


@pytest.mark.marge_only
async def test_services_include_camera(rest):
    """GET /api/services includes camera domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    domains = [s["domain"] for s in services]
    assert "camera" in domains


@pytest.mark.marge_only
async def test_services_include_device_tracker(rest):
    """GET /api/services includes device_tracker domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    domains = [s["domain"] for s in services]
    assert "device_tracker" in domains


@pytest.mark.marge_only
async def test_services_total_domain_count(rest):
    """GET /api/services returns at least 35 domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    assert len(services) >= 34, f"Expected 34+ domains, got {len(services)}"
