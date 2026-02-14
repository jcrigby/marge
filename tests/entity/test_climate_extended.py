"""
CTS -- Climate Extended Service Tests

Tests climate service handlers: set_temperature (with target_temp_high/low),
set_hvac_mode, set_fan_mode, set_preset_mode, set_swing_mode,
and turn_on/turn_off.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_climate_set_temperature(rest):
    """climate.set_temperature stores temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ct_{tag}"
    await rest.set_state(eid, "heat")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_temperature",
        json={"entity_id": eid, "temperature": 72},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72
    assert state["state"] == "heat"  # preserves current state


async def test_climate_set_temperature_high_low(rest):
    """climate.set_temperature with target_temp_high/low stores both."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.chl_{tag}"
    await rest.set_state(eid, "auto")

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_temperature",
        json={
            "entity_id": eid,
            "target_temp_high": 78,
            "target_temp_low": 68,
        },
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["target_temp_high"] == 78
    assert state["attributes"]["target_temp_low"] == 68


async def test_climate_set_hvac_mode(rest):
    """climate.set_hvac_mode changes state to the mode."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.chm_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_hvac_mode",
        json={"entity_id": eid, "hvac_mode": "cool"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "cool"


async def test_climate_set_fan_mode(rest):
    """climate.set_fan_mode stores fan_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.cfm_{tag}"
    await rest.set_state(eid, "heat")

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_fan_mode",
        json={"entity_id": eid, "fan_mode": "high"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["fan_mode"] == "high"
    assert state["state"] == "heat"  # preserves state


async def test_climate_set_preset_mode(rest):
    """climate.set_preset_mode stores preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.cpm_{tag}"
    await rest.set_state(eid, "auto")

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_preset_mode",
        json={"entity_id": eid, "preset_mode": "eco"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "eco"


async def test_climate_set_swing_mode(rest):
    """climate.set_swing_mode stores swing_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.csm_{tag}"
    await rest.set_state(eid, "cool")

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_swing_mode",
        json={"entity_id": eid, "swing_mode": "vertical"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["swing_mode"] == "vertical"


async def test_climate_turn_on(rest):
    """climate.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.con_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_climate_turn_off(rest):
    """climate.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.coff_{tag}"
    await rest.set_state(eid, "heat")

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_climate_lifecycle(rest):
    """Climate lifecycle: off → heat → cool → auto → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.clc_{tag}"
    await rest.set_state(eid, "off")

    for mode in ["heat", "cool", "auto", "off"]:
        await rest.client.post(
            f"{rest.base_url}/api/services/climate/set_hvac_mode",
            json={"entity_id": eid, "hvac_mode": mode},
            headers=rest._headers(),
        )
        state = await rest.get_state(eid)
        assert state["state"] == mode


async def test_climate_temperature_preserves_across_mode_changes(rest):
    """Temperature attribute survives HVAC mode changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctp_{tag}"
    await rest.set_state(eid, "heat")

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_temperature",
        json={"entity_id": eid, "temperature": 72},
        headers=rest._headers(),
    )

    await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_hvac_mode",
        json={"entity_id": eid, "hvac_mode": "cool"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "cool"
    # Attributes are preserved from the current state
    assert state["attributes"].get("temperature") == 72
