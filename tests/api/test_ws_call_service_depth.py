"""
CTS -- WebSocket call_service Depth Tests

Tests WS call_service for various domain handlers: climate set operations,
fan percentage, cover position, media_player controls, lock open,
and entity array support.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_climate_set_temperature(ws, rest):
    """WS call_service climate/set_temperature stores temp."""
    await rest.set_state("climate.ws_clim_st", "heat")
    resp = await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        service_data={"entity_id": "climate.ws_clim_st", "temperature": 72},
    )
    assert resp["success"] is True
    state = await rest.get_state("climate.ws_clim_st")
    assert state["attributes"]["temperature"] == 72


async def test_ws_climate_set_hvac_mode(ws, rest):
    """WS call_service climate/set_hvac_mode changes state."""
    await rest.set_state("climate.ws_clim_hm", "off")
    resp = await ws.send_command(
        "call_service",
        domain="climate",
        service="set_hvac_mode",
        service_data={"entity_id": "climate.ws_clim_hm", "hvac_mode": "cool"},
    )
    assert resp["success"] is True
    state = await rest.get_state("climate.ws_clim_hm")
    assert state["state"] == "cool"


async def test_ws_fan_set_percentage(ws, rest):
    """WS call_service fan/set_percentage stores percentage."""
    await rest.set_state("fan.ws_fan_pct", "on")
    resp = await ws.send_command(
        "call_service",
        domain="fan",
        service="set_percentage",
        service_data={"entity_id": "fan.ws_fan_pct", "percentage": 75},
    )
    assert resp["success"] is True
    state = await rest.get_state("fan.ws_fan_pct")
    assert state["attributes"]["percentage"] == 75


async def test_ws_cover_set_position(ws, rest):
    """WS call_service cover/set_cover_position stores position."""
    await rest.set_state("cover.ws_cov_pos", "closed")
    resp = await ws.send_command(
        "call_service",
        domain="cover",
        service="set_cover_position",
        service_data={"entity_id": "cover.ws_cov_pos", "position": 50},
    )
    assert resp["success"] is True
    state = await rest.get_state("cover.ws_cov_pos")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 50


async def test_ws_media_player_play(ws, rest):
    """WS call_service media_player/media_play sets playing."""
    await rest.set_state("media_player.ws_mp_play", "paused")
    resp = await ws.send_command(
        "call_service",
        domain="media_player",
        service="media_play",
        service_data={"entity_id": "media_player.ws_mp_play"},
    )
    assert resp["success"] is True
    state = await rest.get_state("media_player.ws_mp_play")
    assert state["state"] == "playing"


async def test_ws_lock_open(ws, rest):
    """WS call_service lock/open sets state to open."""
    await rest.set_state("lock.ws_lock_open", "locked")
    resp = await ws.send_command(
        "call_service",
        domain="lock",
        service="open",
        service_data={"entity_id": "lock.ws_lock_open"},
    )
    assert resp["success"] is True
    state = await rest.get_state("lock.ws_lock_open")
    assert state["state"] == "open"


async def test_ws_entity_id_array(ws, rest):
    """WS call_service with entity_id array in service_data."""
    for i in range(3):
        await rest.set_state(f"light.ws_arr_{i}", "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={
            "entity_id": ["light.ws_arr_0", "light.ws_arr_1", "light.ws_arr_2"],
        },
    )
    assert resp["success"] is True
    changed = resp["result"]
    assert isinstance(changed, list)
    assert len(changed) == 3


async def test_ws_vacuum_start(ws, rest):
    """WS call_service vacuum/start sets cleaning."""
    await rest.set_state("vacuum.ws_vac", "idle")
    resp = await ws.send_command(
        "call_service",
        domain="vacuum",
        service="start",
        service_data={"entity_id": "vacuum.ws_vac"},
    )
    assert resp["success"] is True
    state = await rest.get_state("vacuum.ws_vac")
    assert state["state"] == "cleaning"


async def test_ws_humidifier_set_humidity(ws, rest):
    """WS call_service humidifier/set_humidity stores humidity."""
    await rest.set_state("humidifier.ws_hum", "on")
    resp = await ws.send_command(
        "call_service",
        domain="humidifier",
        service="set_humidity",
        service_data={"entity_id": "humidifier.ws_hum", "humidity": 55},
    )
    assert resp["success"] is True
    state = await rest.get_state("humidifier.ws_hum")
    assert state["attributes"]["humidity"] == 55


async def test_ws_number_set_value(ws, rest):
    """WS call_service number/set_value stores value."""
    await rest.set_state("number.ws_num", "0")
    resp = await ws.send_command(
        "call_service",
        domain="number",
        service="set_value",
        service_data={"entity_id": "number.ws_num", "value": 42},
    )
    assert resp["success"] is True


async def test_ws_select_option(ws, rest):
    """WS call_service select/select_option changes state."""
    await rest.set_state("select.ws_sel", "opt_a")
    resp = await ws.send_command(
        "call_service",
        domain="select",
        service="select_option",
        service_data={"entity_id": "select.ws_sel", "option": "opt_b"},
    )
    assert resp["success"] is True
    state = await rest.get_state("select.ws_sel")
    assert state["state"] == "opt_b"
