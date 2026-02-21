"""
CTS -- Service Data Validation Tests

Tests service call data field handling: brightness int/float,
color arrays, temperature types, and extra/missing fields.
"""

import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_light_brightness_int(rest):
    """light.turn_on with integer brightness."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_data_int_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "brightness": 128},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 128


async def test_light_brightness_float(rest):
    """light.turn_on with float brightness rounds/stores."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_data_float_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "brightness": 128.5},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_light_rgb_array(rest):
    """light.turn_on with rgb_color as [R, G, B] array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_rgb_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "rgb_color": [255, 128, 0]},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["rgb_color"] == [255, 128, 0]


async def test_climate_temperature_int(rest):
    """climate.set_temperature with integer temperature."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.svc_temp_{tag}"
    await rest.set_state(eid, "heat")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_temperature",
        json={"entity_id": eid, "temperature": 72},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72


async def test_climate_temperature_float(rest):
    """climate.set_temperature with float temperature."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.svc_temp_f_{tag}"
    await rest.set_state(eid, "cool")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/climate/set_temperature",
        json={"entity_id": eid, "temperature": 22.5},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 22.5


async def test_fan_percentage_boundary_0(rest):
    """fan.set_percentage with 0 (minimum)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.svc_pct_0_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/fan/set_percentage",
        json={"entity_id": eid, "percentage": 0},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fan_percentage_boundary_100(rest):
    """fan.set_percentage with 100 (maximum)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.svc_pct_100_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/fan/set_percentage",
        json={"entity_id": eid, "percentage": 100},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["percentage"] == 100


async def test_cover_position_boundary(rest):
    """cover.set_cover_position with 0 and 100."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.svc_pos_{tag}"
    await rest.set_state(eid, "open")

    # Set to 0
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/cover/set_cover_position",
        json={"entity_id": eid, "position": 0},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["attributes"]["current_position"] == 0

    # Set to 100
    resp2 = await rest.client.post(
        f"{rest.base_url}/api/services/cover/set_cover_position",
        json={"entity_id": eid, "position": 100},
        headers=rest._headers(),
    )
    assert resp2.status_code == 200
    state2 = await rest.get_state(eid)
    assert state2["attributes"]["current_position"] == 100


async def test_media_player_volume_float(rest):
    """media_player.volume_set with float 0.0-1.0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.svc_vol_{tag}"
    await rest.set_state(eid, "playing")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/media_player/volume_set",
        json={"entity_id": eid, "volume_level": 0.75},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.75


async def test_extra_service_data_ignored(rest):
    """Extra fields in service data don't cause errors."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_extra_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={
            "entity_id": eid,
            "brightness": 200,
            "nonexistent_field": "should be ignored",
            "another_junk": 42,
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_service_with_no_entity_id(rest):
    """Service call with no entity_id doesn't crash."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"brightness": 100},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_target_pattern_entity_id(rest):
    """Service call with target.entity_id pattern."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.svc_target_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"target": {"entity_id": eid}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"
