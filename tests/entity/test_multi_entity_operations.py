"""
CTS -- Multi-Entity Operations Tests

Tests operations that affect multiple entities simultaneously:
multi-entity service calls, bulk state reads, and cross-entity
dependency scenarios.
"""

import asyncio
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Multi-Entity Service Calls ───────────────────────────

async def test_turn_on_multiple_lights(rest):
    """Turn on multiple lights in one service call."""
    for i in range(3):
        await rest.set_state(f"light.multi_{i}", "off")

    for i in range(3):
        await rest.call_service("light", "turn_on", {
            "entity_id": f"light.multi_{i}",
        })

    for i in range(3):
        state = await rest.get_state(f"light.multi_{i}")
        assert state["state"] == "on"


async def test_turn_off_multiple_switches(rest):
    """Turn off multiple switches."""
    for i in range(3):
        await rest.set_state(f"switch.multi_sw_{i}", "on")

    for i in range(3):
        await rest.call_service("switch", "turn_off", {
            "entity_id": f"switch.multi_sw_{i}",
        })

    for i in range(3):
        state = await rest.get_state(f"switch.multi_sw_{i}")
        assert state["state"] == "off"


async def test_toggle_multiple_entities(rest):
    """Toggle multiple entities of different starting states."""
    await rest.set_state("switch.multi_tog_a", "on")
    await rest.set_state("switch.multi_tog_b", "off")

    await rest.call_service("switch", "toggle", {"entity_id": "switch.multi_tog_a"})
    await rest.call_service("switch", "toggle", {"entity_id": "switch.multi_tog_b"})

    a = await rest.get_state("switch.multi_tog_a")
    b = await rest.get_state("switch.multi_tog_b")
    assert a["state"] == "off"
    assert b["state"] == "on"


# ── Bulk State Operations ────────────────────────────────

async def test_get_all_states_includes_created(rest):
    """GET /api/states includes recently created entities."""
    entity = "sensor.multi_bulk_check"
    await rest.set_state(entity, "visible")

    states = await rest.get_states()
    ids = [s["entity_id"] for s in states]
    assert entity in ids


async def test_get_states_returns_all_fields(rest):
    """All entries in states list have required fields."""
    states = await rest.get_states()
    for s in states[:10]:
        assert "entity_id" in s
        assert "state" in s
        assert "attributes" in s
        assert "last_changed" in s
        assert "last_updated" in s
        assert "context" in s


async def test_create_many_entities(rest):
    """Creating many entities all appear in states."""
    n = 20
    for i in range(n):
        await rest.set_state(f"sensor.multi_batch_{i}", str(i))

    states = await rest.get_states()
    ids = {s["entity_id"] for s in states}
    for i in range(n):
        assert f"sensor.multi_batch_{i}" in ids


# ── Cross-Domain Operations ──────────────────────────────

async def test_homeassistant_turn_on_multiple_domains(rest):
    """homeassistant.turn_on works across multiple domains."""
    await rest.set_state("light.multi_ha_lt", "off")
    await rest.set_state("switch.multi_ha_sw", "off")
    await rest.set_state("fan.multi_ha_fan", "off")

    for eid in ["light.multi_ha_lt", "switch.multi_ha_sw", "fan.multi_ha_fan"]:
        await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})

    for eid in ["light.multi_ha_lt", "switch.multi_ha_sw", "fan.multi_ha_fan"]:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on"


async def test_homeassistant_turn_off_multiple_domains(rest):
    """homeassistant.turn_off works across multiple domains."""
    await rest.set_state("light.multi_ha_off_lt", "on")
    await rest.set_state("switch.multi_ha_off_sw", "on")

    for eid in ["light.multi_ha_off_lt", "switch.multi_ha_off_sw"]:
        await rest.call_service("homeassistant", "turn_off", {"entity_id": eid})

    for eid in ["light.multi_ha_off_lt", "switch.multi_ha_off_sw"]:
        state = await rest.get_state(eid)
        assert state["state"] == "off", f"{eid} should be off"


# ── State Isolation ──────────────────────────────────────

async def test_entities_are_isolated(rest):
    """Changing one entity does not affect another."""
    await rest.set_state("sensor.multi_iso_a", "100")
    await rest.set_state("sensor.multi_iso_b", "200")

    await rest.set_state("sensor.multi_iso_a", "150")

    a = await rest.get_state("sensor.multi_iso_a")
    b = await rest.get_state("sensor.multi_iso_b")
    assert a["state"] == "150"
    assert b["state"] == "200"  # unchanged


async def test_attributes_are_isolated(rest):
    """Attributes of one entity don't leak to another."""
    await rest.set_state("sensor.multi_attr_a", "x", {"color": "red"})
    await rest.set_state("sensor.multi_attr_b", "y", {"color": "blue"})

    a = await rest.get_state("sensor.multi_attr_a")
    b = await rest.get_state("sensor.multi_attr_b")
    assert a["attributes"]["color"] == "red"
    assert b["attributes"]["color"] == "blue"


async def test_service_calls_are_isolated(rest):
    """Service call on one entity doesn't change another."""
    await rest.set_state("light.multi_svc_a", "on")
    await rest.set_state("light.multi_svc_b", "on")

    await rest.call_service("light", "turn_off", {"entity_id": "light.multi_svc_a"})

    a = await rest.get_state("light.multi_svc_a")
    b = await rest.get_state("light.multi_svc_b")
    assert a["state"] == "off"
    assert b["state"] == "on"  # unchanged
