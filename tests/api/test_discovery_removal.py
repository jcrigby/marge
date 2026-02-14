"""
CTS -- MQTT Discovery Removal and Availability Tests

Tests entity removal via empty discovery payload and availability tracking
through MQTT discovery protocol.
"""

import asyncio
import json
import time

import httpx
import paho.mqtt.client as mqtt
import pytest

BASE = "http://localhost:8124"
MQTT_HOST = "localhost"
MQTT_PORT = 1884
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        if r.status_code == 404:
            return None
        return r.json()


def mqtt_publish(topic: str, payload: str, retain: bool = True):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-rm-{topic.replace('/', '-')[:20]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=retain)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


@pytest.mark.asyncio
async def test_discovery_create_then_remove():
    """Empty discovery payload removes the entity."""
    topic = "homeassistant/switch/disc_rm1/config"
    payload = json.dumps({
        "name": "Removable Switch",
        "unique_id": "disc_rm1",
        "state_topic": "home/switch/disc_rm1/state",
        "command_topic": "home/switch/disc_rm1/set",
    })
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("switch.disc_rm1")
    assert state is not None
    assert state["state"] == "off"

    # Remove via empty payload
    mqtt_publish(topic, "")
    await asyncio.sleep(0.5)

    state = await get_state("switch.disc_rm1")
    assert state is not None
    assert state["state"] == "unavailable"


@pytest.mark.asyncio
async def test_discovery_removal_idempotent():
    """Removing already-removed entity does not crash."""
    topic = "homeassistant/sensor/disc_rm2/config"
    payload = json.dumps({
        "name": "Temp Sensor",
        "unique_id": "disc_rm2",
        "state_topic": "sensors/disc_rm2",
    })
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)

    # Remove twice
    mqtt_publish(topic, "")
    await asyncio.sleep(0.3)
    mqtt_publish(topic, "")
    await asyncio.sleep(0.3)

    # Should not error — entity is just unavailable
    state = await get_state("sensor.disc_rm2")
    assert state is not None


@pytest.mark.asyncio
async def test_discovery_recreate_after_removal():
    """Entity can be recreated after removal."""
    topic = "homeassistant/light/disc_rm3/config"
    payload = json.dumps({
        "name": "Recreatable Light",
        "unique_id": "disc_rm3",
        "state_topic": "home/light/disc_rm3/state",
        "command_topic": "home/light/disc_rm3/set",
    })

    # Create
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)
    s1 = await get_state("light.disc_rm3")
    assert s1["state"] == "off"

    # Remove
    mqtt_publish(topic, "")
    await asyncio.sleep(0.5)
    s2 = await get_state("light.disc_rm3")
    assert s2["state"] == "unavailable"

    # Recreate
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)
    s3 = await get_state("light.disc_rm3")
    assert s3["state"] == "off"


@pytest.mark.asyncio
async def test_discovery_availability_online():
    """Publishing 'online' to availability topic keeps entity available."""
    config_topic = "homeassistant/sensor/disc_avail1/config"
    avail_topic = "home/sensor/disc_avail1/availability"
    payload = json.dumps({
        "name": "Avail Sensor",
        "unique_id": "disc_avail1",
        "state_topic": "home/sensor/disc_avail1/state",
        "availability_topic": avail_topic,
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    # Set state first
    mqtt_publish("home/sensor/disc_avail1/state", "42")
    await asyncio.sleep(0.3)

    # Mark online
    mqtt_publish(avail_topic, "online")
    await asyncio.sleep(0.3)

    state = await get_state("sensor.disc_avail1")
    assert state is not None


@pytest.mark.asyncio
async def test_discovery_availability_offline():
    """Publishing 'offline' to availability topic marks entity unavailable."""
    config_topic = "homeassistant/sensor/disc_avail2/config"
    avail_topic = "home/sensor/disc_avail2/availability"
    payload = json.dumps({
        "name": "Offline Sensor",
        "unique_id": "disc_avail2",
        "state_topic": "home/sensor/disc_avail2/state",
        "availability_topic": avail_topic,
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    # Mark offline
    mqtt_publish(avail_topic, "offline")
    await asyncio.sleep(0.3)

    state = await get_state("sensor.disc_avail2")
    assert state is not None
    assert state["state"] == "unavailable"


@pytest.mark.asyncio
async def test_discovery_climate_multiple_topics():
    """Climate discovery with temperature and mode state topics."""
    config_topic = "homeassistant/climate/disc_clim1/config"
    payload = json.dumps({
        "name": "Test Climate",
        "unique_id": "disc_clim1",
        "temperature_command_topic": "climate/disc_clim1/temp/set",
        "temperature_state_topic": "climate/disc_clim1/temp/state",
        "mode_command_topic": "climate/disc_clim1/mode/set",
        "mode_state_topic": "climate/disc_clim1/mode/state",
        "modes": ["off", "heat", "cool", "auto"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("climate.disc_clim1")
    assert state is not None
    assert state["state"] == "off"
    assert "hvac_modes" in state["attributes"]


@pytest.mark.asyncio
async def test_discovery_cover_position_topic():
    """Cover discovery with position topic."""
    config_topic = "homeassistant/cover/disc_cov1/config"
    payload = json.dumps({
        "name": "Test Cover",
        "unique_id": "disc_cov1",
        "state_topic": "home/cover/disc_cov1/state",
        "command_topic": "home/cover/disc_cov1/set",
        "position_topic": "home/cover/disc_cov1/position",
        "set_position_topic": "home/cover/disc_cov1/position/set",
        "device_class": "garage",
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("cover.disc_cov1")
    assert state is not None
    assert state["state"] == "closed"
    assert state["attributes"].get("device_class") == "garage"


@pytest.mark.asyncio
async def test_discovery_fan_speed_range():
    """Fan discovery with speed_range_max."""
    config_topic = "homeassistant/fan/disc_fan1/config"
    payload = json.dumps({
        "name": "Test Fan",
        "unique_id": "disc_fan1",
        "state_topic": "home/fan/disc_fan1/state",
        "command_topic": "home/fan/disc_fan1/set",
        "percentage_command_topic": "home/fan/disc_fan1/pct/set",
        "percentage_state_topic": "home/fan/disc_fan1/pct/state",
        "speed_range_max": 4,
        "preset_modes": ["auto", "breeze", "silent"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("fan.disc_fan1")
    assert state is not None
    assert state["state"] == "off"


@pytest.mark.asyncio
async def test_discovery_lock_payloads():
    """Lock discovery with custom payload_lock/unlock."""
    config_topic = "homeassistant/lock/disc_lock1/config"
    payload = json.dumps({
        "name": "Test Lock",
        "unique_id": "disc_lock1",
        "state_topic": "home/lock/disc_lock1/state",
        "command_topic": "home/lock/disc_lock1/set",
        "payload_lock": "LOCK",
        "payload_unlock": "UNLOCK",
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("lock.disc_lock1")
    assert state is not None
    assert state["state"] == "locked"


@pytest.mark.asyncio
async def test_discovery_light_color_modes():
    """Light discovery with supported_color_modes and effect_list."""
    config_topic = "homeassistant/light/disc_lt1/config"
    payload = json.dumps({
        "name": "Color Light",
        "unique_id": "disc_lt1",
        "state_topic": "home/light/disc_lt1/state",
        "command_topic": "home/light/disc_lt1/set",
        "supported_color_modes": ["brightness", "color_temp", "rgb"],
        "effect_list": ["rainbow", "strobe", "calm"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("light.disc_lt1")
    assert state is not None
    assert "supported_color_modes" in state["attributes"]
    assert "effect_list" in state["attributes"]


@pytest.mark.asyncio
async def test_discovery_number_attributes():
    """Number discovery with min/max/step/mode."""
    config_topic = "homeassistant/number/disc_num1/config"
    payload = json.dumps({
        "name": "Test Number",
        "unique_id": "disc_num1",
        "state_topic": "home/number/disc_num1/state",
        "command_topic": "home/number/disc_num1/set",
        "min": 0,
        "max": 100,
        "step": 5,
        "mode": "slider",
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("number.disc_num1")
    assert state is not None
    assert state["attributes"].get("min") == 0
    assert state["attributes"].get("max") == 100
    assert state["attributes"].get("step") == 5
    assert state["attributes"].get("mode") == "slider"


@pytest.mark.asyncio
async def test_discovery_select_options():
    """Select discovery with options list."""
    config_topic = "homeassistant/select/disc_sel1/config"
    payload = json.dumps({
        "name": "Test Select",
        "unique_id": "disc_sel1",
        "state_topic": "home/select/disc_sel1/state",
        "command_topic": "home/select/disc_sel1/set",
        "options": ["option1", "option2", "option3"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("select.disc_sel1")
    assert state is not None
    assert state["attributes"].get("options") == ["option1", "option2", "option3"]


@pytest.mark.asyncio
async def test_discovery_node_id_topic():
    """Discovery with 5-segment topic (node_id present)."""
    topic = "homeassistant/sensor/z2m_bridge/disc_node1/config"
    payload = json.dumps({
        "name": "Node Sensor",
        "unique_id": "disc_node1",
        "state_topic": "home/sensor/disc_node1/state",
    })
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.disc_node1")
    assert state is not None
