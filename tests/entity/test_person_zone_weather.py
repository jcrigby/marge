"""
CTS -- Person, Zone, Weather Domain Service Tests

Tests person.set_state, zone entity management, and weather entity
attribute handling for these less-common domains.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_person_set_state(rest):
    """person entity can be set and read."""
    tag = uuid.uuid4().hex[:8]
    eid = f"person.user_{tag}"
    await rest.set_state(eid, "home", {"friendly_name": f"User {tag}"})
    state = await rest.get_state(eid)
    assert state["state"] == "home"
    assert state["attributes"]["friendly_name"] == f"User {tag}"


async def test_person_state_transitions(rest):
    """person entity tracks location changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"person.traveler_{tag}"
    await rest.set_state(eid, "home")

    await rest.set_state(eid, "not_home")
    state = await rest.get_state(eid)
    assert state["state"] == "not_home"

    await rest.set_state(eid, "work")
    state = await rest.get_state(eid)
    assert state["state"] == "work"


async def test_zone_entity(rest):
    """zone entity with lat/lon/radius."""
    tag = uuid.uuid4().hex[:8]
    eid = f"zone.office_{tag}"
    await rest.set_state(eid, "0", {
        "friendly_name": "Office",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 100,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["latitude"] == 37.7749
    assert state["attributes"]["longitude"] == -122.4194
    assert state["attributes"]["radius"] == 100


async def test_zone_multiple(rest):
    """Multiple zones can coexist."""
    tag = uuid.uuid4().hex[:8]
    zones = ["home", "work", "gym"]
    for name in zones:
        eid = f"zone.{name}_{tag}"
        await rest.set_state(eid, "0", {"friendly_name": name.title()})

    for name in zones:
        eid = f"zone.{name}_{tag}"
        state = await rest.get_state(eid)
        assert state is not None


async def test_weather_entity(rest):
    """weather entity with forecast attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"weather.local_{tag}"
    await rest.set_state(eid, "sunny", {
        "temperature": 72,
        "humidity": 45,
        "wind_speed": 12,
        "friendly_name": "Local Weather",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "sunny"
    assert state["attributes"]["temperature"] == 72
    assert state["attributes"]["humidity"] == 45


async def test_weather_state_changes(rest):
    """weather entity state can change (sunny -> cloudy)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"weather.forecast_{tag}"
    await rest.set_state(eid, "sunny")
    await rest.set_state(eid, "cloudy")
    state = await rest.get_state(eid)
    assert state["state"] == "cloudy"


async def test_image_entity(rest):
    """image entity stores URL and metadata."""
    tag = uuid.uuid4().hex[:8]
    eid = f"image.camera_{tag}"
    await rest.set_state(eid, "idle", {
        "entity_picture": "/local/camera.jpg",
        "friendly_name": f"Camera {tag}",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "idle"
    assert state["attributes"]["entity_picture"] == "/local/camera.jpg"


async def test_script_entity(rest):
    """script entity can be set."""
    tag = uuid.uuid4().hex[:8]
    eid = f"script.my_script_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": f"Script {tag}"})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_group_entity(rest):
    """group entity with entity_id list attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.lights_{tag}"
    await rest.set_state(eid, "on", {
        "entity_id": [f"light.a_{tag}", f"light.b_{tag}"],
        "friendly_name": "All Lights",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert isinstance(state["attributes"]["entity_id"], list)
    assert len(state["attributes"]["entity_id"]) == 2


@pytest.mark.marge_only
async def test_number_entity_set_value(rest):
    """number entity set_value service."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.volume_{tag}"
    await rest.set_state(eid, "50")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/number/set_value",
        json={"entity_id": eid, "value": 75},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "75"


@pytest.mark.marge_only
async def test_select_entity_select_option(rest):
    """select entity select_option service."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.mode_{tag}"
    await rest.set_state(eid, "auto", {"options": ["auto", "heat", "cool"]})

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/select/select_option",
        json={"entity_id": eid, "option": "heat"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "heat"


async def test_button_press(rest):
    """button entity press service."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.reboot_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/button/press",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
