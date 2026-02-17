# Plan: Virtual Device Simulator Containers

## Context

The demo currently uses static MQTT entities in `ha-config/configuration.yaml` with the scenario driver publishing raw strings to `home/{domain}/{object_id}/state` topics. Neither Marge nor HA exercises their auto-discovery code paths. Virtual device containers speak the **real protocols** (zigbee2mqtt MQTT Discovery, Shelly HTTP, Hue HTTP) so both systems discover and control devices exactly as they would with real hardware. Enables side-by-side all-virtual demo.

## Architecture

```
virtual-z2m-ha   ──MQTT──→ mosquitto:1883 ──→ ha-legacy (8123)
virtual-z2m-marge──MQTT──→ marge:1884         marge     (8124)
virtual-shelly   ──HTTP──→ polled by Marge (and optionally HA)
virtual-hue      ──HTTP──→ polled by Marge (and optionally HA)
```

Two zigbee2mqtt instances (one per broker). Shelly/Hue are single HTTP servers.

## File Structure

```
virtual-devices/
  zigbee2mqtt/
    Dockerfile              (python:3.12-slim)
    requirements.txt        (paho-mqtt>=2.0)
    simulator.py            (~400 LOC)
    devices.py              (~200 LOC)
  shelly/
    Dockerfile
    requirements.txt        (fastapi, uvicorn)
    simulator.py            (~200 LOC)
  hue/
    Dockerfile
    requirements.txt        (fastapi, uvicorn)
    simulator.py            (~250 LOC)
```

## Files to Modify

- `docker-compose.yml` — add 4 services under `virtual` profile
- `ha-config/configuration-virtual.yaml` — new file, same as configuration.yaml minus `mqtt:` block

## Execution: 3 Subagents

### Agent 1: virtual-zigbee2mqtt

**`devices.py`** (~200 LOC):
- Device fleet as list of dicts, 46 devices matching demo home exactly
- `build_discovery_payload(device)` — HA MQTT Discovery JSON
- `build_bridge_devices()` — zigbee2mqtt bridge/devices array
- `object_id` field ensures entity IDs match (`light.bedroom`, `sensor.bedroom_temperature`, etc.)

Device fleet: 9 lights (bedroom dimmable+CT, bathroom, kitchen, 4x living room dimmable, porch, pathway), 1 switch (coffee_maker), 1 climate (thermostat 55-90F), 2 locks, 1 alarm, 4 motion sensors, 3 door contacts, 2 safety sensors, 6 temp sensors, 6 humidity sensors, 3 power sensors.

Discovery: `homeassistant/{component}/0x{ieee}/{object_id}/config` (retained)
State: `zigbee2mqtt/{friendly_name}` (JSON)
Commands: `zigbee2mqtt/{friendly_name}/set` (JSON)
Lights: `"schema": "json"`

**`simulator.py`** (~400 LOC):
- paho-mqtt v2, threading.Timer for periodic loop
- **on_connect**: publish bridge/state, discovery configs, bridge/devices, availability, initial states
- **on_message**: handle `zigbee2mqtt/+/set` commands, update state, echo back
- **periodic** (5s): temp drift, humidity drift, power walk, random motion triggers (5% chance, 30s cooldown)

### Agent 2: virtual-shelly + virtual-hue

**Shelly** (~200 LOC FastAPI):
- 2 Gen2 devices (relay+power, dimmer)
- `GET /shelly`, `GET /rpc/Shelly.GetStatus`, `GET /rpc/Switch.Set`, `GET /rpc/Light.Set`
- Background power/temp drift

**Hue** (~250 LOC FastAPI):
- Bridge with 3 lights + 2 sensors (ZLLPresence, ZLLTemperature)
- `POST /api` (pair), `GET /api/{user}/config|lights|sensors`, `PUT /api/{user}/lights/{id}/state`
- Background sensor drift

### Agent 3: docker-compose + HA virtual config

- 4 services in docker-compose.yml under `virtual` profile
- `ha-config/configuration-virtual.yaml` (no mqtt: block — discovery handles entities)
- Port mapping: virtual-shelly 8180, virtual-hue 8181

## Key Protocol Details

### zigbee2mqtt MQTT Discovery

Discovery topic format: `homeassistant/{component}/0x{ieee_address}/{object_id}/config`

Example light (dimmable + color temp):
```json
{
  "name": "Bedroom", "unique_id": "0x00158d0000000001_light",
  "object_id": "bedroom",
  "state_topic": "zigbee2mqtt/Bedroom",
  "command_topic": "zigbee2mqtt/Bedroom/set",
  "availability_topic": "zigbee2mqtt/Bedroom/availability",
  "schema": "json",
  "brightness": true, "brightness_scale": 254, "color_temp": true,
  "supported_color_modes": ["brightness", "color_temp"],
  "device": {
    "identifiers": ["0x00158d0000000001"],
    "name": "Bedroom", "manufacturer": "IKEA", "model": "LED1545G12"
  }
}
```

Example binary sensor (motion):
```json
{
  "name": "Entryway Motion", "unique_id": "0x00158d0000000010_occupancy",
  "object_id": "entryway_motion",
  "state_topic": "zigbee2mqtt/Entryway Motion",
  "device_class": "motion", "payload_on": "ON", "payload_off": "OFF",
  "value_template": "{{ value_json.occupancy }}",
  "device": {
    "identifiers": ["0x00158d0000000010"],
    "name": "Entryway Motion", "manufacturer": "Aqara", "model": "RTCGQ11LM"
  }
}
```

### Shelly Gen2 HTTP API

- `GET /shelly` → `{"id": "shellyplus1pm-aabb01020304", "mac": "AABB01020304", "gen": 2}`
- `GET /rpc/Shelly.GetStatus` → `{"sys": {...}, "switch:0": {"output": true, "apower": 45.2, ...}}`
- `GET /rpc/Switch.Set?id=0&on=true` → `{"was_on": false}`

### Hue Bridge HTTP API

- `POST /api` → `[{"success": {"username": "virtual-hue-user"}}]`
- `GET /api/{user}/lights` → `{"1": {"name": "...", "state": {"on": true, "bri": 254, ...}, ...}}`
- `GET /api/{user}/sensors` → `{"1": {"type": "ZLLPresence", "state": {"presence": false}, ...}}`
- `PUT /api/{user}/lights/{id}/state` → `[{"success": {...}}]`

## Verification

1. `docker compose --profile virtual up -d mosquitto virtual-z2m-ha`
2. `mosquitto_sub -t 'homeassistant/#' -v -C 5` — discovery payloads appear
3. `mosquitto_sub -t 'zigbee2mqtt/#' -v -C 10` — bridge state + device states
4. Start Marge, `curl localhost:8124/api/states` — entities discovered
5. `mosquitto_pub -t 'zigbee2mqtt/Bedroom/set' -m '{"state":"ON"}'` — command echo works
6. `curl localhost:8180/shelly` — Shelly identity
7. `curl localhost:8181/api/test/lights` — Hue lights
8. Full stack: both HA and Marge discover same 46 entities independently
