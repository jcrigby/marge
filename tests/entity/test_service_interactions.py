"""
CTS -- Complex Service Interaction Tests

Tests service calls that involve multiple attributes, state
transitions, and domain-specific semantics.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# -- Light Services --

async def test_light_turn_on_with_brightness(rest):
    """light.turn_on with brightness sets attribute."""
    await rest.set_state("light.svc_int_bright", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.svc_int_bright",
        "brightness": 200,
    })
    state = await rest.get_state("light.svc_int_bright")
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_light_turn_on_with_color(rest):
    """light.turn_on with rgb_color sets attribute."""
    await rest.set_state("light.svc_int_color", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.svc_int_color",
        "rgb_color": [255, 0, 0],
    })
    state = await rest.get_state("light.svc_int_color")
    assert state["state"] == "on"
    assert state["attributes"]["rgb_color"] == [255, 0, 0]


async def test_light_toggle_from_on(rest):
    """light.toggle from on switches to off."""
    await rest.set_state("light.svc_int_toggle", "on")
    await rest.call_service("light", "toggle", {
        "entity_id": "light.svc_int_toggle",
    })
    state = await rest.get_state("light.svc_int_toggle")
    assert state["state"] == "off"


async def test_light_toggle_from_off(rest):
    """light.toggle from off switches to on."""
    await rest.set_state("light.svc_int_toggle2", "off")
    await rest.call_service("light", "toggle", {
        "entity_id": "light.svc_int_toggle2",
    })
    state = await rest.get_state("light.svc_int_toggle2")
    assert state["state"] == "on"


# -- Climate Services --

async def test_climate_set_multiple_attributes(rest):
    """climate.set_temperature sets temperature attribute."""
    await rest.set_state("climate.svc_int_multi", "heat")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": "climate.svc_int_multi",
        "temperature": 68,
    })
    state = await rest.get_state("climate.svc_int_multi")
    assert state["attributes"]["temperature"] == 68


# -- Cover Services --

async def test_cover_toggle_from_open(rest):
    """cover.toggle from open switches to closed."""
    await rest.set_state("cover.svc_int_ctoggle", "open")
    await rest.call_service("cover", "toggle", {
        "entity_id": "cover.svc_int_ctoggle",
    })
    state = await rest.get_state("cover.svc_int_ctoggle")
    assert state["state"] == "closed"


# -- Media Player Services --

async def test_media_player_volume_set(rest):
    """media_player.volume_set sets volume_level attribute."""
    await rest.set_state("media_player.svc_int_vol", "playing")
    await rest.call_service("media_player", "volume_set", {
        "entity_id": "media_player.svc_int_vol",
        "volume_level": 0.75,
    })
    state = await rest.get_state("media_player.svc_int_vol")
    assert state["attributes"]["volume_level"] == 0.75


async def test_media_player_shuffle_set(rest):
    """media_player.shuffle_set sets shuffle attribute."""
    await rest.set_state("media_player.svc_int_shuf", "playing")
    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": "media_player.svc_int_shuf",
        "shuffle": True,
    })
    state = await rest.get_state("media_player.svc_int_shuf")
    assert state["attributes"]["shuffle"] is True


async def test_media_player_source(rest):
    """media_player.select_source sets source attribute."""
    await rest.set_state("media_player.svc_int_src", "playing")
    await rest.call_service("media_player", "select_source", {
        "entity_id": "media_player.svc_int_src",
        "source": "HDMI 1",
    })
    state = await rest.get_state("media_player.svc_int_src")
    assert state["attributes"]["source"] == "HDMI 1"


async def test_media_player_state_transitions(rest):
    """media_player state transitions: play -> pause -> stop."""
    entity = "media_player.svc_int_trans"
    await rest.set_state(entity, "idle")
    await rest.call_service("media_player", "media_play", {"entity_id": entity})
    state = await rest.get_state(entity)
    assert state["state"] == "playing"

    await rest.call_service("media_player", "media_pause", {"entity_id": entity})
    state = await rest.get_state(entity)
    assert state["state"] == "paused"

    await rest.call_service("media_player", "media_stop", {"entity_id": entity})
    state = await rest.get_state(entity)
    assert state["state"] == "idle"


# -- Input Helpers --

async def test_input_select_option(rest):
    """input_select.select_option sets state to option."""
    await rest.set_state("input_select.svc_int_is", "A")
    await rest.call_service("input_select", "select_option", {
        "entity_id": "input_select.svc_int_is",
        "option": "B",
    })
    state = await rest.get_state("input_select.svc_int_is")
    assert state["state"] == "B"
