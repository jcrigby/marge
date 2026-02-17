#!/usr/bin/env python3
"""Virtual zigbee2mqtt simulator -- speaks real z2m MQTT protocol.

Publishes HA MQTT Discovery configs, bridge state, device availability,
and live device states. Handles set commands and runs a periodic tick
to drift sensor values and trigger motion events.

Environment variables:
    MQTT_HOST       Broker hostname (default: localhost)
    MQTT_PORT       Broker port     (default: 1883)
    BRIDGE_NAME     z2m bridge name (default: zigbee2mqtt)
    TICK_INTERVAL   Seconds between sensor ticks (default: 5)
"""

import json
import logging
import os
import random
import sys
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from devices import (
    DEVICES,
    build_discovery_payload,
    build_bridge_devices,
    build_initial_state,
)

# ── Configuration ───────────────────────────────────────────────────

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
BRIDGE_NAME = os.environ.get("BRIDGE_NAME", "zigbee2mqtt")
TICK_INTERVAL = float(os.environ.get("TICK_INTERVAL", "5"))

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("z2m-sim")

# ── Runtime State ───────────────────────────────────────────────────

# device state keyed by friendly_name -> dict
device_states = {}

# device lookup by friendly_name -> device dict
device_by_name = {}

# motion auto-clear timers: friendly_name -> threading.Timer
motion_timers = {}

# lock for state mutations
state_lock = threading.Lock()


# ── Helpers ─────────────────────────────────────────────────────────

def publish_json(client, topic, payload, retain=True):
    """Publish a JSON-serialized payload."""
    msg = json.dumps(payload, separators=(",", ":"))
    client.publish(topic, msg, qos=1, retain=retain)


def publish_state(client, device):
    """Publish current state for a device."""
    fname = device["friendly_name"]
    topic = f"{BRIDGE_NAME}/{fname}"
    with state_lock:
        state = device_states.get(fname, {})
    publish_json(client, topic, state)


# ── MQTT Callbacks ──────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    """Connected to broker -- publish all discovery, state, and subscribe."""
    if reason_code != 0:
        log.error("Connection failed: %s", reason_code)
        return

    log.info("Connected to MQTT broker %s:%d", MQTT_HOST, MQTT_PORT)

    # 1. Bridge state
    client.publish(
        f"{BRIDGE_NAME}/bridge/state",
        json.dumps({"state": "online"}),
        qos=1, retain=True,
    )
    log.info("Published bridge state: online")

    # 2. Bridge info
    bridge_info = {
        "version": "1.40.1",
        "commit": "virtual-sim",
        "coordinator": {
            "ieee_address": "0x00124b0018ed2a5c",
            "type": "zStack3x0",
            "meta": {"revision": 20240315, "transportrev": 2},
        },
        "log_level": "info",
        "permit_join": False,
        "config": {},
    }
    publish_json(client, f"{BRIDGE_NAME}/bridge/info", bridge_info)
    log.info("Published bridge info")

    # 3. Discovery configs
    for dev in DEVICES:
        topic, payload = build_discovery_payload(dev)
        publish_json(client, topic, payload)
    log.info("Published %d discovery configs", len(DEVICES))

    # 4. Bridge devices list
    publish_json(client, f"{BRIDGE_NAME}/bridge/devices", build_bridge_devices())
    log.info("Published bridge/devices (%d devices)", len(DEVICES))

    # 5. Device availability + initial state
    for dev in DEVICES:
        fname = dev["friendly_name"]
        # Availability
        client.publish(
            f"{BRIDGE_NAME}/{fname}/availability",
            "online", qos=1, retain=True,
        )
        # Initial state
        with state_lock:
            if fname not in device_states:
                device_states[fname] = build_initial_state(dev)
        publish_state(client, dev)

    log.info("Published availability + initial state for %d devices", len(DEVICES))

    # 6. Subscribe to set commands
    client.subscribe(f"{BRIDGE_NAME}/+/set", qos=1)
    client.subscribe(f"{BRIDGE_NAME}/+/set/#", qos=1)
    log.info("Subscribed to %s/+/set and %s/+/set/#", BRIDGE_NAME, BRIDGE_NAME)


def on_disconnect(client, userdata, flags, reason_code, properties):
    """Disconnected from broker."""
    log.warning("Disconnected from broker (reason=%s), will reconnect...", reason_code)


def on_message(client, userdata, msg):
    """Handle incoming set commands on zigbee2mqtt/{name}/set[/subpath]."""
    topic = msg.topic
    payload_raw = msg.payload.decode("utf-8", errors="replace")

    # Parse topic: zigbee2mqtt/{friendly_name}/set[/subfield]
    parts = topic.split("/")
    if len(parts) < 3 or parts[0] != BRIDGE_NAME or parts[2] != "set":
        return

    fname = parts[1]
    subfield = "/".join(parts[3:]) if len(parts) > 3 else None

    dev = device_by_name.get(fname)
    if dev is None:
        log.warning("Set command for unknown device: %s", fname)
        return

    comp = dev["component"]

    # Parse payload -- could be JSON or bare string
    try:
        cmd = json.loads(payload_raw)
    except json.JSONDecodeError:
        cmd = payload_raw.strip()

    log.info("CMD %s [%s] subfield=%s payload=%s", fname, comp, subfield, cmd)

    with state_lock:
        state = device_states.setdefault(fname, {})
        _handle_set(dev, state, cmd, subfield)

    publish_state(client, dev)


def _handle_set(device, state, cmd, subfield):
    """Apply a set command to device state (called under state_lock)."""
    comp = device["component"]

    if comp == "light":
        _handle_light_set(device, state, cmd)
    elif comp == "switch":
        _handle_switch_set(state, cmd)
    elif comp == "climate":
        _handle_climate_set(state, cmd, subfield)
    elif comp == "lock":
        _handle_lock_set(state, cmd)
    elif comp == "alarm_control_panel":
        _handle_alarm_set(state, cmd)


def _handle_light_set(device, state, cmd):
    """Process light set command (JSON schema or bare string)."""
    if isinstance(cmd, str):
        state["state"] = cmd.upper()
        if cmd.upper() == "OFF" and device.get("brightness"):
            state["brightness"] = 0
        return

    if isinstance(cmd, dict):
        if "state" in cmd:
            state["state"] = cmd["state"].upper()
        if "brightness" in cmd:
            state["brightness"] = max(0, min(254, int(cmd["brightness"])))
            if state["brightness"] > 0:
                state["state"] = "ON"
        if "color_temp" in cmd:
            state["color_temp"] = int(cmd["color_temp"])
        if state.get("state") == "OFF" and device.get("brightness"):
            state["brightness"] = 0


def _handle_switch_set(state, cmd):
    """Process switch set command."""
    if isinstance(cmd, str):
        state["state"] = cmd.upper()
    elif isinstance(cmd, dict) and "state" in cmd:
        state["state"] = cmd["state"].upper()


def _handle_climate_set(state, cmd, subfield):
    """Process climate set command.

    Commands arrive either as:
      - zigbee2mqtt/Thermostat/set {"system_mode":"cool","current_heating_setpoint":72}
      - zigbee2mqtt/Thermostat/set/system_mode "cool"
      - zigbee2mqtt/Thermostat/set/current_heating_setpoint 72
    """
    if subfield == "system_mode":
        val = cmd if isinstance(cmd, str) else str(cmd)
        state["system_mode"] = val.strip('"')
    elif subfield == "current_heating_setpoint":
        try:
            state["current_heating_setpoint"] = float(cmd)
        except (ValueError, TypeError):
            pass
    elif isinstance(cmd, dict):
        if "system_mode" in cmd:
            state["system_mode"] = cmd["system_mode"]
        if "current_heating_setpoint" in cmd:
            state["current_heating_setpoint"] = float(cmd["current_heating_setpoint"])
    elif isinstance(cmd, str):
        # bare mode string
        state["system_mode"] = cmd.strip('"')


def _handle_lock_set(state, cmd):
    """Process lock set command."""
    if isinstance(cmd, str):
        val = cmd.upper()
        if val == "LOCK":
            state["state"] = "LOCKED"
        elif val == "UNLOCK":
            state["state"] = "UNLOCKED"
    elif isinstance(cmd, dict) and "state" in cmd:
        val = cmd["state"].upper()
        if val == "LOCK":
            state["state"] = "LOCKED"
        elif val == "UNLOCK":
            state["state"] = "UNLOCKED"


def _handle_alarm_set(state, cmd):
    """Process alarm control panel set command."""
    _ALARM_MAP = {
        "DISARM": "disarmed",
        "ARM_HOME": "armed_home",
        "ARM_AWAY": "armed_away",
        "ARM_NIGHT": "armed_night",
    }
    if isinstance(cmd, str):
        val = cmd.upper()
        if val in _ALARM_MAP:
            state["state"] = _ALARM_MAP[val]
    elif isinstance(cmd, dict) and "state" in cmd:
        val = cmd["state"].upper()
        if val in _ALARM_MAP:
            state["state"] = _ALARM_MAP[val]


# ── Periodic Sensor Tick ────────────────────────────────────────────

def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def run_tick(client):
    """Run one sensor tick -- drift values and publish changes."""
    changed = []

    with state_lock:
        for dev in DEVICES:
            fname = dev["friendly_name"]
            comp = dev["component"]
            state = device_states.get(fname, {})

            if comp == "sensor":
                if _tick_sensor(dev, state):
                    changed.append(dev)

            elif comp == "binary_sensor" and dev.get("device_class") == "motion":
                if _tick_motion(dev, state, client):
                    changed.append(dev)

            elif comp == "climate":
                if _tick_climate(state):
                    changed.append(dev)

    # Publish changed states outside lock
    for dev in changed:
        publish_state(client, dev)


def _tick_sensor(device, state):
    """Drift sensor values. Returns True if changed."""
    dc = device.get("device_class", "")
    vk = device.get("value_key", "state")
    obj_id = device["object_id"]

    if dc == "temperature":
        old = state.get(vk, 70.0)
        is_exterior = "exterior" in obj_id
        lo, hi = (30.0, 90.0) if is_exterior else (60.0, 85.0)
        state[vk] = round(_clamp(old + random.uniform(-0.3, 0.3), lo, hi), 1)
        return True

    if dc == "humidity":
        old = state.get(vk, 45.0)
        state[vk] = round(_clamp(old + random.uniform(-0.5, 0.5), 25.0, 70.0), 1)
        return True

    if dc == "power":
        old = state.get(vk, 820.0)
        state[vk] = round(_clamp(old + random.uniform(-20, 20), 200.0, 2000.0), 1)
        return True

    if dc == "voltage":
        old = state.get(vk, 120.3)
        state[vk] = round(_clamp(old + random.uniform(-0.5, 0.5), 118.0, 122.0), 1)
        return True

    if dc == "current":
        # Recalculate from power / voltage
        power_dev = device_by_name.get("Power Monitor")
        voltage_dev = device_by_name.get("Voltage Monitor")
        if power_dev and voltage_dev:
            p_state = device_states.get("Power Monitor", {})
            v_state = device_states.get("Voltage Monitor", {})
            pwr = p_state.get("power", 820.0)
            vol = v_state.get("voltage", 120.3)
            if vol > 0:
                state[vk] = round(pwr / vol, 2)
                return True
        return False

    return False


def _tick_motion(device, state, client):
    """5% chance to trigger motion ON, auto-clear after 30s. Returns True if triggered."""
    fname = device["friendly_name"]
    vk = device.get("value_key", "occupancy")

    # Only trigger if not already active
    if state.get(vk, False):
        return False

    if random.random() < 0.05:
        state[vk] = True

        # Schedule auto-clear
        def clear_motion():
            with state_lock:
                s = device_states.get(fname, {})
                s[vk] = False
            publish_state(client, device)
            log.debug("Motion cleared: %s", fname)

        # Cancel any existing timer
        old_timer = motion_timers.get(fname)
        if old_timer:
            old_timer.cancel()

        timer = threading.Timer(30.0, clear_motion)
        timer.daemon = True
        timer.start()
        motion_timers[fname] = timer

        log.info("Motion triggered: %s", fname)
        return True

    return False


def _tick_climate(state):
    """Drift thermostat current temp toward setpoint. Returns True if changed."""
    mode = state.get("system_mode", "off")
    current = state.get("local_temperature", 68.0)
    setpoint = state.get("current_heating_setpoint", 70.0)

    if mode == "heat" and current < setpoint:
        state["local_temperature"] = round(current + 0.1, 1)
        return True
    elif mode == "cool" and current > setpoint:
        state["local_temperature"] = round(current - 0.1, 1)
        return True
    elif mode == "heat_cool":
        if current < setpoint - 1:
            state["local_temperature"] = round(current + 0.1, 1)
            return True
        elif current > setpoint + 1:
            state["local_temperature"] = round(current - 0.1, 1)
            return True

    return False


def tick_loop(client):
    """Background thread running periodic sensor ticks."""
    log.info("Tick loop started (interval=%.1fs)", TICK_INTERVAL)
    while True:
        try:
            run_tick(client)
        except Exception:
            log.exception("Error in tick loop")
        time.sleep(TICK_INTERVAL)


# ── Main ────────────────────────────────────────────────────────────

def main():
    log.info("Virtual zigbee2mqtt simulator starting")
    log.info("  Broker: %s:%d", MQTT_HOST, MQTT_PORT)
    log.info("  Devices: %d", len(DEVICES))
    log.info("  Tick interval: %.1fs", TICK_INTERVAL)

    # Build device lookup
    for dev in DEVICES:
        device_by_name[dev["friendly_name"]] = dev

    # Initialize states
    for dev in DEVICES:
        device_states[dev["friendly_name"]] = build_initial_state(dev)

    # Create MQTT client (paho v2 API)
    client_id = f"virtual-z2m-{random.randint(1000, 9999)}"
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Set LWT so bridge goes offline if we crash
    client.will_set(
        f"{BRIDGE_NAME}/bridge/state",
        json.dumps({"state": "offline"}),
        qos=1, retain=True,
    )

    # Start tick thread
    tick_thread = threading.Thread(target=tick_loop, args=(client,), daemon=True)
    tick_thread.start()

    # Connect and run
    log.info("Connecting to %s:%d as %s ...", MQTT_HOST, MQTT_PORT, client_id)
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except Exception as exc:
        log.error("Failed to connect: %s", exc)
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        # Publish offline before exit
        client.publish(
            f"{BRIDGE_NAME}/bridge/state",
            json.dumps({"state": "offline"}),
            qos=1, retain=True,
        )
        client.disconnect()
        log.info("Goodbye.")


if __name__ == "__main__":
    main()
