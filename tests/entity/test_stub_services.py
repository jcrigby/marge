"""
CTS -- Stub Service Tests

Tests service calls for domains with stub handlers
(no state change, just returns success) and edge cases
for generic domain services.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Script Services ──────────────────────────────────────────

async def test_script_turn_on(rest):
    """script.turn_on returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/script/turn_on",
        json={"entity_id": "script.test_stub"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_script_reload(rest):
    """script.reload returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/script/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Notify Service ───────────────────────────────────────────

async def test_notify_send_message(rest):
    """notify.send_message returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/notify/send_message",
        json={"message": "Hello from CTS"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Weather Service ──────────────────────────────────────────

async def test_weather_get_forecasts(rest):
    """weather.get_forecasts returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/weather/get_forecasts",
        json={"entity_id": "weather.home"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Image Service ────────────────────────────────────────────

async def test_image_reload(rest):
    """image.reload returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/image/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Person/Zone Reload ───────────────────────────────────────

async def test_person_reload(rest):
    """person.reload returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/person/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_zone_reload(rest):
    """zone.reload returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/zone/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Homeassistant Services ───────────────────────────────────

async def test_homeassistant_restart(rest):
    """homeassistant.restart returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/restart",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_homeassistant_stop(rest):
    """homeassistant.stop returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/stop",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_homeassistant_reload_core_config(rest):
    """homeassistant.reload_core_config returns 200 (stub)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/reload_core_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Button Press ─────────────────────────────────────────────

async def test_button_press(rest):
    """button.press returns 200 (stub, logs press)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/button/press",
        json={"entity_id": "button.test_doorbell"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Input Datetime ───────────────────────────────────────────

async def test_input_datetime_set(rest):
    """input_datetime.set_datetime sets state to datetime string."""
    await rest.set_state("input_datetime.alarm_time", "00:00:00")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": "input_datetime.alarm_time",
        "datetime": "2026-02-13 07:30:00",
    })
    state = await rest.get_state("input_datetime.alarm_time")
    assert state["state"] == "2026-02-13 07:30:00"


async def test_input_datetime_set_time(rest):
    """input_datetime.set_datetime with time only."""
    await rest.set_state("input_datetime.wakeup", "00:00:00")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": "input_datetime.wakeup",
        "time": "08:15:00",
    })
    state = await rest.get_state("input_datetime.wakeup")
    assert state["state"] == "08:15:00"


# ── Generic Turn On/Off/Toggle ────────────────────────────────

async def test_homeassistant_turn_on_generic(rest):
    """homeassistant.turn_on sets entity to on."""
    await rest.set_state("switch.ha_generic_test", "off")
    await rest.call_service("homeassistant", "turn_on", {
        "entity_id": "switch.ha_generic_test",
    })
    state = await rest.get_state("switch.ha_generic_test")
    assert state["state"] == "on"


async def test_homeassistant_turn_off_generic(rest):
    """homeassistant.turn_off sets entity to off."""
    await rest.set_state("switch.ha_generic_off", "on")
    await rest.call_service("homeassistant", "turn_off", {
        "entity_id": "switch.ha_generic_off",
    })
    state = await rest.get_state("switch.ha_generic_off")
    assert state["state"] == "off"


async def test_homeassistant_toggle_generic(rest):
    """homeassistant.toggle flips entity state."""
    await rest.set_state("switch.ha_toggle_test", "off")
    await rest.call_service("homeassistant", "toggle", {
        "entity_id": "switch.ha_toggle_test",
    })
    state = await rest.get_state("switch.ha_toggle_test")
    assert state["state"] == "on"
