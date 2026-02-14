"""
CTS -- Generic Fallback Service Handler Tests

Tests that the generic fallback service handlers (turn_on, turn_off,
toggle) work for any domain, even those without explicit registrations.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_unknown_domain_turn_on(rest):
    """Generic turn_on works for unregistered domain."""
    await rest.set_state("custom_domain.fallback_1", "off")
    await rest.call_service("custom_domain", "turn_on", {
        "entity_id": "custom_domain.fallback_1",
    })
    state = await rest.get_state("custom_domain.fallback_1")
    assert state["state"] == "on"


async def test_unknown_domain_turn_off(rest):
    """Generic turn_off works for unregistered domain."""
    await rest.set_state("custom_domain.fallback_2", "on")
    await rest.call_service("custom_domain", "turn_off", {
        "entity_id": "custom_domain.fallback_2",
    })
    state = await rest.get_state("custom_domain.fallback_2")
    assert state["state"] == "off"


async def test_unknown_domain_toggle_on_to_off(rest):
    """Generic toggle works for unregistered domain."""
    await rest.set_state("custom_domain.fallback_3", "on")
    await rest.call_service("custom_domain", "toggle", {
        "entity_id": "custom_domain.fallback_3",
    })
    state = await rest.get_state("custom_domain.fallback_3")
    assert state["state"] == "off"


async def test_unknown_domain_toggle_off_to_on(rest):
    """Generic toggle from off to on for unregistered domain."""
    await rest.set_state("custom_domain.fallback_4", "off")
    await rest.call_service("custom_domain", "toggle", {
        "entity_id": "custom_domain.fallback_4",
    })
    state = await rest.get_state("custom_domain.fallback_4")
    assert state["state"] == "on"


async def test_fallback_preserves_attrs(rest):
    """Generic fallback service preserves entity attributes."""
    await rest.set_state("custom_domain.fallback_5", "off", {"custom_key": "custom_val"})
    await rest.call_service("custom_domain", "turn_on", {
        "entity_id": "custom_domain.fallback_5",
    })
    state = await rest.get_state("custom_domain.fallback_5")
    assert state["state"] == "on"
    assert state["attributes"]["custom_key"] == "custom_val"


async def test_fallback_unknown_service(rest):
    """Unknown service for unknown domain returns 200 (no state change)."""
    await rest.set_state("custom_domain.fallback_6", "initial")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/custom_domain/unknown_service",
        json={"entity_id": "custom_domain.fallback_6"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # State should not have changed
    state = await rest.get_state("custom_domain.fallback_6")
    assert state["state"] == "initial"


async def test_binary_sensor_domain_fallback(rest):
    """binary_sensor domain uses generic fallback."""
    await rest.set_state("binary_sensor.fallback_bs", "off")
    await rest.call_service("binary_sensor", "turn_on", {
        "entity_id": "binary_sensor.fallback_bs",
    })
    state = await rest.get_state("binary_sensor.fallback_bs")
    assert state["state"] == "on"
