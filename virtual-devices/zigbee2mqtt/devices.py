"""Virtual zigbee2mqtt device fleet — matches demo home in ha-config/configuration.yaml.

46 devices total: 9 lights, 1 switch, 1 climate, 2 locks, 1 alarm,
9 binary sensors, 14 sensors, 9 power-monitoring devices (embedded in sensors).

Each device dict drives:
  - HA MQTT Discovery config publication
  - zigbee2mqtt bridge/devices payload
  - Initial state JSON on the device state topic
"""

import json

# ── IEEE address generator ──────────────────────────────────────────
_IEEE_BASE = 0x00158D0001000000


def _ieee(n):
    return f"0x{_IEEE_BASE + n:016x}"


# ── Device Fleet ────────────────────────────────────────────────────

DEVICES = [
    # ── LIGHTS (9) ──────────────────────────────────────────────────
    {
        "ieee": _ieee(1), "friendly_name": "Bedroom",
        "type": "Router", "model": "LED1545G12", "vendor": "IKEA",
        "component": "light", "object_id": "bedroom",
        "brightness": True, "color_temp": True, "schema": "json",
    },
    {
        "ieee": _ieee(2), "friendly_name": "Bathroom",
        "type": "Router", "model": "LED1623G12", "vendor": "IKEA",
        "component": "light", "object_id": "bathroom",
    },
    {
        "ieee": _ieee(3), "friendly_name": "Kitchen",
        "type": "Router", "model": "LED1623G12", "vendor": "IKEA",
        "component": "light", "object_id": "kitchen",
    },
    {
        "ieee": _ieee(4), "friendly_name": "Living Room Main",
        "type": "Router", "model": "LED1545G12", "vendor": "IKEA",
        "component": "light", "object_id": "living_room_main",
        "brightness": True, "schema": "json",
    },
    {
        "ieee": _ieee(5), "friendly_name": "Living Room Accent",
        "type": "Router", "model": "LED1545G12", "vendor": "IKEA",
        "component": "light", "object_id": "living_room_accent",
        "brightness": True, "schema": "json",
    },
    {
        "ieee": _ieee(6), "friendly_name": "Living Room Lamp",
        "type": "Router", "model": "LED1545G12", "vendor": "IKEA",
        "component": "light", "object_id": "living_room_lamp",
        "brightness": True, "schema": "json",
    },
    {
        "ieee": _ieee(7), "friendly_name": "Living Room Floor",
        "type": "Router", "model": "LED1545G12", "vendor": "IKEA",
        "component": "light", "object_id": "living_room_floor",
        "brightness": True, "schema": "json",
    },
    {
        "ieee": _ieee(8), "friendly_name": "Porch",
        "type": "Router", "model": "LED1623G12", "vendor": "IKEA",
        "component": "light", "object_id": "porch",
    },
    {
        "ieee": _ieee(9), "friendly_name": "Pathway",
        "type": "Router", "model": "LED1623G12", "vendor": "IKEA",
        "component": "light", "object_id": "pathway",
    },

    # ── SWITCH (1) ──────────────────────────────────────────────────
    {
        "ieee": _ieee(10), "friendly_name": "Coffee Maker",
        "type": "Router", "model": "TS011F", "vendor": "TuYa",
        "component": "switch", "object_id": "coffee_maker",
    },

    # ── CLIMATE (1) ─────────────────────────────────────────────────
    {
        "ieee": _ieee(11), "friendly_name": "Thermostat",
        "type": "Router", "model": "ZEN-01", "vendor": "Zen",
        "component": "climate", "object_id": "thermostat",
        "modes": ["off", "heat", "cool", "heat_cool"],
        "min_temp": 55, "max_temp": 90,
    },

    # ── LOCKS (2) ───────────────────────────────────────────────────
    {
        "ieee": _ieee(12), "friendly_name": "Front Door Lock",
        "type": "EndDevice", "model": "YRD256", "vendor": "Yale",
        "component": "lock", "object_id": "front_door",
    },
    {
        "ieee": _ieee(13), "friendly_name": "Back Door Lock",
        "type": "EndDevice", "model": "YRD256", "vendor": "Yale",
        "component": "lock", "object_id": "back_door",
    },

    # ── ALARM (1) ───────────────────────────────────────────────────
    {
        "ieee": _ieee(14), "friendly_name": "Home Alarm",
        "type": "Router", "model": "IAS-ACE", "vendor": "Generic",
        "component": "alarm_control_panel", "object_id": "home",
    },

    # ── BINARY SENSORS (9) ──────────────────────────────────────────
    {
        "ieee": _ieee(15), "friendly_name": "Entryway Motion",
        "type": "EndDevice", "model": "RTCGQ11LM", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "entryway_motion",
        "device_class": "motion", "value_key": "occupancy",
    },
    {
        "ieee": _ieee(16), "friendly_name": "Kitchen Motion",
        "type": "EndDevice", "model": "RTCGQ11LM", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "kitchen_motion",
        "device_class": "motion", "value_key": "occupancy",
    },
    {
        "ieee": _ieee(17), "friendly_name": "Living Room Motion",
        "type": "EndDevice", "model": "RTCGQ11LM", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "living_room_motion",
        "device_class": "motion", "value_key": "occupancy",
    },
    {
        "ieee": _ieee(18), "friendly_name": "Bedroom Motion",
        "type": "EndDevice", "model": "RTCGQ11LM", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "bedroom_motion",
        "device_class": "motion", "value_key": "occupancy",
    },
    {
        "ieee": _ieee(19), "friendly_name": "Front Door Contact",
        "type": "EndDevice", "model": "MCCGQ11LM", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "front_door_contact",
        "device_class": "door", "value_key": "contact",
    },
    {
        "ieee": _ieee(20), "friendly_name": "Back Door Contact",
        "type": "EndDevice", "model": "MCCGQ11LM", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "back_door_contact",
        "device_class": "door", "value_key": "contact",
    },
    {
        "ieee": _ieee(21), "friendly_name": "Garage Door",
        "type": "EndDevice", "model": "MCCGQ11LM", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "garage_door_contact",
        "device_class": "garage_door", "value_key": "contact",
    },
    {
        "ieee": _ieee(22), "friendly_name": "Smoke Detector",
        "type": "EndDevice", "model": "JTYJ-GD-01LM/BW", "vendor": "Xiaomi",
        "component": "binary_sensor", "object_id": "smoke_detector",
        "device_class": "smoke", "value_key": "smoke",
    },
    {
        "ieee": _ieee(23), "friendly_name": "CO Detector",
        "type": "EndDevice", "model": "HS1CA-M", "vendor": "HEIMAN",
        "component": "binary_sensor", "object_id": "co_detector",
        "device_class": "gas", "value_key": "gas",
    },

    # ── SENSORS — Temperature (6) ──────────────────────────────────
    {
        "ieee": _ieee(24), "friendly_name": "Bedroom Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "bedroom_temperature",
        "device_class": "temperature", "unit": "\u00b0F",
        "value_key": "temperature",
    },
    {
        "ieee": _ieee(25), "friendly_name": "Kitchen Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "kitchen_temperature",
        "device_class": "temperature", "unit": "\u00b0F",
        "value_key": "temperature",
    },
    {
        "ieee": _ieee(26), "friendly_name": "Living Room Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "living_room_temperature",
        "device_class": "temperature", "unit": "\u00b0F",
        "value_key": "temperature",
    },
    {
        "ieee": _ieee(27), "friendly_name": "Bathroom Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "bathroom_temperature",
        "device_class": "temperature", "unit": "\u00b0F",
        "value_key": "temperature",
    },
    {
        "ieee": _ieee(28), "friendly_name": "Entryway Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "entryway_temperature",
        "device_class": "temperature", "unit": "\u00b0F",
        "value_key": "temperature",
    },
    {
        "ieee": _ieee(29), "friendly_name": "Exterior Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "exterior_temperature",
        "device_class": "temperature", "unit": "\u00b0F",
        "value_key": "temperature",
    },

    # ── SENSORS — Humidity (5) ──────────────────────────────────────
    {
        "ieee": _ieee(30), "friendly_name": "Bedroom Humidity Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "bedroom_humidity",
        "device_class": "humidity", "unit": "%",
        "value_key": "humidity",
    },
    {
        "ieee": _ieee(31), "friendly_name": "Kitchen Humidity Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "kitchen_humidity",
        "device_class": "humidity", "unit": "%",
        "value_key": "humidity",
    },
    {
        "ieee": _ieee(32), "friendly_name": "Living Room Humidity Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "living_room_humidity",
        "device_class": "humidity", "unit": "%",
        "value_key": "humidity",
    },
    {
        "ieee": _ieee(33), "friendly_name": "Bathroom Humidity Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "bathroom_humidity",
        "device_class": "humidity", "unit": "%",
        "value_key": "humidity",
    },
    {
        "ieee": _ieee(34), "friendly_name": "Exterior Humidity Sensor",
        "type": "EndDevice", "model": "WSDCGQ11LM", "vendor": "Xiaomi",
        "component": "sensor", "object_id": "exterior_humidity",
        "device_class": "humidity", "unit": "%",
        "value_key": "humidity",
    },

    # ── SENSORS — Power (3) ─────────────────────────────────────────
    {
        "ieee": _ieee(35), "friendly_name": "Power Monitor",
        "type": "Router", "model": "PCZS-111Z", "vendor": "TuYa",
        "component": "sensor", "object_id": "power_consumption",
        "device_class": "power", "unit": "W",
        "value_key": "power",
    },
    {
        "ieee": _ieee(36), "friendly_name": "Voltage Monitor",
        "type": "Router", "model": "PCZS-111Z", "vendor": "TuYa",
        "component": "sensor", "object_id": "voltage",
        "device_class": "voltage", "unit": "V",
        "value_key": "voltage",
    },
    {
        "ieee": _ieee(37), "friendly_name": "Current Monitor",
        "type": "Router", "model": "PCZS-111Z", "vendor": "TuYa",
        "component": "sensor", "object_id": "current",
        "device_class": "current", "unit": "A",
        "value_key": "current",
    },
]

assert len(DEVICES) == 37, f"Expected 37 devices, got {len(DEVICES)}"


# ── Discovery Payload Builder ───────────────────────────────────────

def build_discovery_payload(device):
    """Return (topic, payload_dict) for HA MQTT Discovery.

    Topic format: homeassistant/{component}/{ieee}/{object_id}/config
    """
    comp = device["component"]
    ieee = device["ieee"]
    obj_id = device["object_id"]
    fname = device["friendly_name"]

    topic = f"homeassistant/{comp}/{ieee}/{obj_id}/config"

    state_topic = f"zigbee2mqtt/{fname}"

    payload = {
        "name": device["friendly_name"] if comp not in ("sensor",) else _sensor_display_name(device),
        "unique_id": f"z2m_{ieee}_{obj_id}",
        "object_id": obj_id,
        "state_topic": state_topic,
        "availability": [{"topic": f"zigbee2mqtt/{fname}/availability"}],
        "device": {
            "identifiers": [ieee],
            "manufacturer": device["vendor"],
            "model": device["model"],
            "name": fname,
        },
    }

    # ── Component-specific fields ───────────────────────────────────

    if comp == "light":
        payload["command_topic"] = f"{state_topic}/set"
        payload["payload_on"] = "ON"
        payload["payload_off"] = "OFF"
        if device.get("schema") == "json":
            payload["schema"] = "json"
            payload["state_value_template"] = "{{ value_json.state }}"
        if device.get("brightness"):
            payload["brightness"] = True
            payload["brightness_scale"] = 254
        if device.get("color_temp"):
            payload["color_temp"] = True

    elif comp == "switch":
        payload["command_topic"] = f"{state_topic}/set"
        payload["value_template"] = "{{ value_json.state }}"
        payload["payload_on"] = "ON"
        payload["payload_off"] = "OFF"
        payload["state_on"] = "ON"
        payload["state_off"] = "OFF"

    elif comp == "climate":
        payload["mode_state_topic"] = state_topic
        payload["mode_state_template"] = "{{ value_json.system_mode }}"
        payload["mode_command_topic"] = f"{state_topic}/set/system_mode"
        payload["temperature_state_topic"] = state_topic
        payload["temperature_state_template"] = "{{ value_json.current_heating_setpoint }}"
        payload["temperature_command_topic"] = f"{state_topic}/set/current_heating_setpoint"
        payload["current_temperature_topic"] = state_topic
        payload["current_temperature_template"] = "{{ value_json.local_temperature }}"
        payload["modes"] = device.get("modes", ["off", "heat", "cool", "heat_cool"])
        payload["min_temp"] = device.get("min_temp", 55)
        payload["max_temp"] = device.get("max_temp", 90)
        payload["temp_step"] = 1

    elif comp == "lock":
        payload["command_topic"] = f"{state_topic}/set"
        payload["value_template"] = "{{ value_json.state }}"
        payload["payload_lock"] = "LOCK"
        payload["payload_unlock"] = "UNLOCK"
        payload["state_locked"] = "LOCKED"
        payload["state_unlocked"] = "UNLOCKED"

    elif comp == "alarm_control_panel":
        payload["command_topic"] = f"{state_topic}/set"
        payload["value_template"] = "{{ value_json.state }}"
        payload["payload_disarm"] = "DISARM"
        payload["payload_arm_home"] = "ARM_HOME"
        payload["payload_arm_away"] = "ARM_AWAY"
        payload["payload_arm_night"] = "ARM_NIGHT"

    elif comp == "binary_sensor":
        vk = device.get("value_key", "state")
        payload["value_template"] = "{{ value_json." + vk + " }}"
        payload["payload_on"] = "true" if vk != "contact" else "false"
        payload["payload_off"] = "false" if vk != "contact" else "true"
        if device.get("device_class"):
            payload["device_class"] = device["device_class"]

    elif comp == "sensor":
        vk = device.get("value_key", "state")
        payload["value_template"] = "{{ value_json." + vk + " }}"
        if device.get("device_class"):
            payload["device_class"] = device["device_class"]
        if device.get("unit"):
            payload["unit_of_measurement"] = device["unit"]
        payload["state_class"] = "measurement"

    # Override name for sensors to use proper display name
    if comp == "sensor":
        payload["name"] = _sensor_display_name(device)

    return topic, payload


def _sensor_display_name(device):
    """Produce a human-readable sensor name from the object_id."""
    return device["object_id"].replace("_", " ").title()


# ── Bridge Devices Payload ──────────────────────────────────────────

def build_bridge_devices():
    """Return list of device dicts in zigbee2mqtt bridge/devices format."""
    result = []
    for dev in DEVICES:
        result.append({
            "ieee_address": dev["ieee"],
            "friendly_name": dev["friendly_name"],
            "type": dev["type"],
            "network_address": hash(dev["ieee"]) & 0xFFFF,
            "supported": True,
            "interview_completed": True,
            "definition": {
                "model": dev["model"],
                "vendor": dev["vendor"],
                "description": f"{dev['vendor']} {dev['model']} ({dev['component']})",
            },
        })
    return result


# ── Initial State Builder ───────────────────────────────────────────

_DEFAULT_TEMPS = {
    "bedroom_temperature": 70.2,
    "kitchen_temperature": 71.5,
    "living_room_temperature": 69.8,
    "bathroom_temperature": 72.1,
    "entryway_temperature": 68.4,
    "exterior_temperature": 45.3,
}

_DEFAULT_HUMIDITY = {
    "bedroom_humidity": 42.0,
    "kitchen_humidity": 48.0,
    "living_room_humidity": 44.0,
    "bathroom_humidity": 55.0,
    "exterior_humidity": 62.0,
}


def build_initial_state(device):
    """Return dict of initial JSON state for zigbee2mqtt/{friendly_name}."""
    comp = device["component"]
    obj_id = device["object_id"]

    if comp == "light":
        state = {"state": "OFF"}
        if device.get("brightness"):
            state["brightness"] = 0
        if device.get("color_temp"):
            state["color_temp"] = 350
        return state

    if comp == "switch":
        return {"state": "OFF"}

    if comp == "climate":
        return {
            "system_mode": "heat",
            "current_heating_setpoint": 70,
            "local_temperature": 68.0,
        }

    if comp == "lock":
        return {"state": "LOCKED"}

    if comp == "alarm_control_panel":
        return {"state": "disarmed"}

    if comp == "binary_sensor":
        dc = device.get("device_class", "")
        vk = device.get("value_key", "state")
        if dc == "motion":
            return {vk: False}
        if dc in ("door", "garage_door"):
            # contact=true means closed (no intrusion)
            return {vk: True}
        # smoke, gas
        return {vk: False}

    if comp == "sensor":
        vk = device.get("value_key", "state")
        dc = device.get("device_class", "")
        if dc == "temperature":
            return {vk: _DEFAULT_TEMPS.get(obj_id, 70.0)}
        if dc == "humidity":
            return {vk: _DEFAULT_HUMIDITY.get(obj_id, 45.0)}
        if dc == "power":
            return {vk: 820.0}
        if dc == "voltage":
            return {vk: 120.3}
        if dc == "current":
            return {vk: 6.8}
        return {vk: 0}

    return {"state": "unknown"}
