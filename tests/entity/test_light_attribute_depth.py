"""
CTS -- Light Attribute Handling Depth Tests

Tests light domain attribute handling for all supported attributes:
brightness, color_temp, rgb_color, xy_color, hs_color, effect, transition.
Also tests attribute preservation across on/off cycles.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_light_brightness(rest):
    """light.turn_on with brightness stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lb_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "brightness": 255},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 255


async def test_light_color_temp(rest):
    """light.turn_on with color_temp stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lct_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "color_temp": 350},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["color_temp"] == 350


async def test_light_rgb_color(rest):
    """light.turn_on with rgb_color stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lrgb_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "rgb_color": [255, 128, 0]},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["rgb_color"] == [255, 128, 0]


async def test_light_xy_color(rest):
    """light.turn_on with xy_color stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lxy_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "xy_color": [0.5, 0.3]},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["xy_color"] == [0.5, 0.3]


async def test_light_hs_color(rest):
    """light.turn_on with hs_color stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lhs_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "hs_color": [30, 100]},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["hs_color"] == [30, 100]


async def test_light_effect(rest):
    """light.turn_on with effect stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.leff_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "effect": "rainbow"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["effect"] == "rainbow"


async def test_light_transition(rest):
    """light.turn_on with transition stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ltr_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "transition": 5},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["transition"] == 5


async def test_light_multiple_attributes(rest):
    """light.turn_on with multiple attributes stores all."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lmulti_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={
            "entity_id": eid,
            "brightness": 200,
            "color_temp": 300,
            "transition": 2,
        },
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 200
    assert state["attributes"]["color_temp"] == 300
    assert state["attributes"]["transition"] == 2


async def test_light_turn_off_preserves_attributes(rest):
    """light.turn_off preserves brightness and other attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lpres_{tag}"
    await rest.set_state(eid, "off")

    # Turn on with brightness
    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "brightness": 128},
        headers=rest._headers(),
    )

    # Turn off
    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"
    # Brightness should be preserved
    assert state["attributes"]["brightness"] == 128


async def test_light_toggle_preserves_attributes(rest):
    """light.toggle preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ltog_{tag}"
    await rest.set_state(eid, "on", {"brightness": 100, "friendly_name": "Test"})

    await rest.client.post(
        f"{rest.base_url}/api/services/light/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 100
    assert state["attributes"]["friendly_name"] == "Test"


async def test_light_brightness_zero(rest):
    """light.turn_on with brightness 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lbz_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "brightness": 0},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 0


async def test_light_on_off_on_cycle(rest):
    """Full on→off→on cycle maintains attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lcyc_{tag}"
    await rest.set_state(eid, "off")

    # On with attributes
    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "brightness": 180, "effect": "strobe"},
        headers=rest._headers(),
    )
    s1 = await rest.get_state(eid)
    assert s1["state"] == "on"

    # Off
    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    s2 = await rest.get_state(eid)
    assert s2["state"] == "off"

    # On again (preserves previous attrs from state)
    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    s3 = await rest.get_state(eid)
    assert s3["state"] == "on"
    assert s3["attributes"]["brightness"] == 180
