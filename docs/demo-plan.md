# MARGE — Innovation Week Demo Spec

**Document Number:** MRG-DEMO-001
**Date:** 2026-02-12
**Prepared For:** The Department of Showing, Not Telling
**Classification:** UNCLASSIFIED // SEND IT

---

## 0. WHAT WE'RE BUILDING

A side-by-side visual demo of Home Assistant and Marge processing the **same simulated day** in a house. Same events. Same automations. Same outcomes. Wildly different operational profiles. Running at 10x real time in Docker containers with an ASCII-roguelike house visualization and a live metrics dashboard.

The demo answers two questions without the presenter having to say a word:
1. What does a production-grade home automation platform look like when built on proper foundations?
2. What happens when you give an LLM agent a rigorous spec instead of a Jira ticket?

**Duration at 10x:** 2.4 hours for the full day, or ~15 minutes for the highlight reel (5 key scenes with time-skip).

---

## 1. THE SIMULATED HOUSE

### 1.1 Floor Plan

```
┌─────────────────────┬──────────────────┬────────────────────┐
│ BEDROOM             │ BATHROOM         │ KITCHEN            │
│                     │                  │                    │
│  💡 Ceiling Light    │  💡 Ceiling Light │  💡 Ceiling Light   │
│  🌡️  Temp Sensor     │  🌡️  Temp Sensor  │  🌡️  Temp Sensor    │
│  👤 Motion Sensor   │  💧 Moisture     │  👤 Motion Sensor  │
│  🌡️  Humidity        │                  │  ☕ Coffee Maker    │
│                     │                  │  🌡️  Humidity       │
├─────────────────────┤                  ├────────────────────┤
│ ENTRYWAY            ├──────────────────┤ LIVING ROOM        │
│                     │                  │                    │
│  🚪 Front Door Lock │                  │  💡 Main Light      │
│  🚪 Back Door Lock  │                  │  💡 Accent Light    │
│  👤 Motion Sensor   │                  │  💡 Lamp            │
│  🌡️  Temp Sensor     │                  │  💡 Floor Light     │
│  📱 Door Contact x2 │                  │  📺 Media Player    │
│                     │                  │  👤 Motion Sensor  │
│                     │                  │  🌡️  Temp + Humidity │
├─────────────────────┴──────────────────┴────────────────────┤
│ EXTERIOR                                                    │
│  💡 Porch Light    💡 Pathway Light    🌡️  Temp + Humidity   │
│  🔒 Alarm Panel    ☀️  Sun Position     🌤️  Weather           │
│  ⚡ Power Monitor   📱 Phone Tracker   🔥 Smoke + CO        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Entity Registry (43 entities)

#### Lights (8)

| Entity ID | Room | Notes |
|---|---|---|
| `light.bedroom` | Bedroom | Dimmable, color_temp. Morning automation target. |
| `light.bathroom` | Bathroom | Simple on/off |
| `light.kitchen` | Kitchen | Simple on/off |
| `light.living_room_main` | Living Room | Dimmable. Evening scene. |
| `light.living_room_accent` | Living Room | Dimmable, rgb. Evening scene. |
| `light.living_room_lamp` | Living Room | Dimmable. Evening scene. |
| `light.living_room_floor` | Living Room | Dimmable. Evening scene. |
| `light.porch` | Exterior | Sunset automation target. |
| `light.pathway` | Exterior | Sunset automation target. |

Note: That's 9 lights. The 4 living room lights + media player = the "Evening" scene (5 entities, matches "4 lights, 1 media player" from TheoryOps).

#### Switches (1)

| Entity ID | Room | Notes |
|---|---|---|
| `switch.coffee_maker` | Kitchen | Morning automation target. Z-Wave in the narrative. |

#### Climate (1)

| Entity ID | Room | Notes |
|---|---|---|
| `climate.thermostat` | Whole house | Night=66°F, Day=70°F. Morning/Goodnight automation target. |

#### Locks (2)

| Entity ID | Room | Notes |
|---|---|---|
| `lock.front_door` | Entryway | Z-Wave. Goodnight verification target. |
| `lock.back_door` | Entryway | Z-Wave. Goodnight verification target. |

#### Binary Sensors (9)

| Entity ID | Device Class | Room | Notes |
|---|---|---|---|
| `binary_sensor.entryway_motion` | motion | Entryway | Security automation trigger |
| `binary_sensor.kitchen_motion` | motion | Kitchen | Background activity |
| `binary_sensor.living_room_motion` | motion | Living Room | Background activity |
| `binary_sensor.bedroom_motion` | motion | Bedroom | Background activity |
| `binary_sensor.front_door_contact` | door | Entryway | 06:15 event |
| `binary_sensor.back_door_contact` | door | Entryway | Background |
| `binary_sensor.garage_door_contact` | garage_door | Exterior | Background |
| `binary_sensor.smoke_detector` | smoke | Whole house | Night monitoring |
| `binary_sensor.co_detector` | gas | Whole house | Night monitoring |

#### Sensors (14)

| Entity ID | Device Class | Unit | Room |
|---|---|---|---|
| `sensor.bedroom_temperature` | temperature | °F | Bedroom |
| `sensor.bedroom_humidity` | humidity | % | Bedroom |
| `sensor.kitchen_temperature` | temperature | °F | Kitchen |
| `sensor.kitchen_humidity` | humidity | % | Kitchen |
| `sensor.living_room_temperature` | temperature | °F | Living Room |
| `sensor.living_room_humidity` | humidity | % | Living Room |
| `sensor.bathroom_temperature` | temperature | °F | Bathroom |
| `sensor.bathroom_humidity` | humidity | % | Bathroom |
| `sensor.entryway_temperature` | temperature | °F | Entryway |
| `sensor.exterior_temperature` | temperature | °F | Exterior |
| `sensor.exterior_humidity` | humidity | % | Exterior |
| `sensor.power_consumption` | power | W | Whole house |
| `sensor.voltage` | voltage | V | Whole house |
| `sensor.current` | current | A | Whole house |

#### Other (8)

| Entity ID | Domain | Notes |
|---|---|---|
| `media_player.living_room` | media_player | Evening scene target |
| `alarm_control_panel.home` | alarm_control_panel | armed_home/armed_away/armed_night/disarmed |
| `weather.home` | weather | Polls every 30 min. Background. |
| `device_tracker.phone` | device_tracker | home/not_home. Background. |
| `scene.evening` | scene | 4 LR lights + media player |
| `scene.goodnight` | scene | All lights off, thermostat night |
| `button.bedside` | button | Triggers goodnight routine |
| `sun.sun` | sun | Sunrise/sunset. Provided by HA natively, simulated for Marge. |

**Total: 43 entities** (matches TheoryOps "~45" estimate)

---

## 2. THE SIX AUTOMATIONS

### Automation 1: Morning Wake-Up

```yaml
- id: morning_wakeup
  alias: "Morning Wake-Up"
  mode: single
  triggers:
    - trigger: time
      at: "05:30:00"
  actions:
    - action: light.turn_on
      target:
        entity_id: light.bedroom
      data:
        brightness: 51          # 20% of 255
        color_temp: 400         # Warm white (mireds)
    - action: climate.set_temperature
      target:
        entity_id: climate.thermostat
      data:
        temperature: 70
    - action: switch.turn_on
      target:
        entity_id: switch.coffee_maker
```

**Trigger:** Time = 05:30
**Actions:** 3 service calls → 4 state changes (light state + brightness + color_temp, thermostat, coffee maker)

### Automation 2: Security Alert

```yaml
- id: security_alert
  alias: "Security Alert — Motion While Armed Away"
  mode: single
  triggers:
    - trigger: state
      entity_id: binary_sensor.entryway_motion
      to: "on"
  conditions:
    - condition: state
      entity_id: alarm_control_panel.home
      state: "armed_away"
  actions:
    - action: persistent_notification.create
      data:
        title: "Security Alert"
        message: "Motion detected in entryway while armed away!"
        notification_id: "security_motion"
```

**Trigger:** Entryway motion → on
**Condition:** Alarm is armed_away
**Action:** Notification (at 06:15 the alarm is armed_home so this does NOT fire — that's the test)

### Automation 3: Sunset Lights

```yaml
- id: sunset_lights
  alias: "Sunset — Exterior and Evening Scene"
  mode: single
  triggers:
    - trigger: sun
      event: sunset
  actions:
    - action: light.turn_on
      target:
        entity_id:
          - light.porch
          - light.pathway
    - action: scene.turn_on
      target:
        entity_id: scene.evening
```

**Trigger:** Sun event = sunset (17:30 in scenario)
**Actions:** Porch + pathway on, Evening scene applied → 6 state changes total

### Automation 4: Evening Scene Definition

```yaml
# This is a scene definition, not an automation
scenes:
  - id: evening
    name: "Evening"
    entities:
      light.living_room_main:
        state: "on"
        brightness: 180
      light.living_room_accent:
        state: "on"
        brightness: 120
        rgb_color: [255, 147, 41]
      light.living_room_lamp:
        state: "on"
        brightness: 150
      light.living_room_floor:
        state: "on"
        brightness: 80
      media_player.living_room:
        state: "on"
        source: "Music"
```

### Automation 5: Goodnight Routine

```yaml
- id: goodnight_routine
  alias: "Goodnight Routine"
  mode: single
  triggers:
    - trigger: state
      entity_id: button.bedside
  actions:
    # All lights off
    - action: light.turn_off
      target:
        entity_id:
          - light.bedroom
          - light.bathroom
          - light.kitchen
          - light.living_room_main
          - light.living_room_accent
          - light.living_room_lamp
          - light.living_room_floor
          - light.porch
          - light.pathway
    # Lock doors
    - action: lock.lock
      target:
        entity_id:
          - lock.front_door
          - lock.back_door
    # Thermostat to night mode
    - action: climate.set_temperature
      target:
        entity_id: climate.thermostat
      data:
        temperature: 66
    # Arm alarm for night
    - action: alarm_control_panel.arm_night
      target:
        entity_id: alarm_control_panel.home
    # Turn off media
    - action: media_player.turn_off
      target:
        entity_id: media_player.living_room
```

**Trigger:** Bedside button pressed
**Actions:** 12+ state changes (9 lights off, 2 locks, thermostat, alarm, media player)

### Automation 6: Lock Verification

```yaml
- id: lock_verification
  alias: "Lock Verification After Goodnight"
  mode: single
  triggers:
    - trigger: state
      entity_id: alarm_control_panel.home
      to: "armed_night"
  conditions:
    - condition: or
      conditions:
        - condition: state
          entity_id: lock.front_door
          state: "unlocked"
        - condition: state
          entity_id: lock.back_door
          state: "unlocked"
  actions:
    - action: persistent_notification.create
      data:
        title: "Lock Alert"
        message: "A door is still unlocked after Goodnight routine!"
        notification_id: "lock_check"
```

**Trigger:** Alarm changes to armed_night
**Condition:** Any lock still unlocked
**Action:** Notification (normally doesn't fire because Automation 5 locks first)

---

## 3. THE SCENARIO TIMELINE

### 3.1 Chapters

The scenario is divided into chapters. The demo driver supports `--chapter <name>` to skip to any chapter.

| Chapter | Sim Time | Duration (10x) | What Happens |
|---|---|---|---|
| `dawn` | 05:25–06:00 | 3.5 min | Morning automation fires. Lights, thermostat, coffee. |
| `morning` | 06:10–06:20 | 1 min | Front door event. Security check (no alert). |
| `daytime` | 06:20–17:25 | 66 min | Steady-state sensor noise. ~2000 state changes. |
| `sunset` | 17:25–17:40 | 1.5 min | Sunset trigger. Exterior lights + evening scene. |
| `evening` | 17:40–21:55 | 25 min | Quiet evening. Occasional sensor updates. |
| `goodnight` | 21:55–22:05 | 1 min | Bedside button. Goodnight routine. 12 state changes. |
| `night` | 22:05–03:45 | 34 min | Night quiet. Smoke/CO monitored. ~200 state changes. |
| `outage` | 03:45–04:15 | 3 min | Power cut. Recovery race. The money shot. |

**Demo highlight reel (for 15-min slot):** dawn → morning → (skip) → sunset → (skip) → goodnight → (skip) → outage. Total: ~10 minutes at 10x.

### 3.2 Event Format

```json
{
  "chapter": "dawn",
  "events": [
    {
      "offset_ms": 0,
      "type": "state",
      "entity_id": "sensor.exterior_temperature",
      "state": "42.1",
      "attributes": {"unit_of_measurement": "°F", "device_class": "temperature"}
    },
    {
      "offset_ms": 300000,
      "type": "time_tick",
      "sim_time": "05:30:00"
    },
    {
      "offset_ms": 300100,
      "type": "annotation",
      "message": "☀️ Morning automation should fire"
    }
  ]
}
```

At 10x speed, `offset_ms` values are divided by 10 for real-time delays.

`type` values:
- `state` — Push entity state update to SUT via REST API or MQTT
- `time_tick` — Inform SUT of current sim-time (for time triggers)
- `sun` — Fire sun event (sunrise/sunset)
- `annotation` — Display message in dashboard timeline (not sent to SUT)
- `verify` — Assert expected state (optional, for automated validation)

### 3.3 Steady-State Background Noise

During `daytime`, `evening`, and `night` chapters, the scenario generates:
- Temperature sensors: ±0.3°F random walk, update every 60s (14 sensors)
- Humidity sensors: ±0.5% random walk, update every 60s (6 sensors)
- Motion sensors: stochastic on/off (higher during daytime, near-zero at night)
- Power consumption: sinusoidal pattern (500W baseline, peaks at morning/evening)
- Voltage/current: near-constant with small noise
- Weather: updates every 30 min
- Device tracker: home during morning/evening, not_home during daytime

---

## 4. TECHNICAL ARCHITECTURE

### 4.1 Container Layout

```
┌──────────────────────────────────────────────────────────┐
│                     Docker Compose                        │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  mosquitto   │  │  ha-legacy  │  │     marge       │  │
│  │  (MQTT       │  │  (HA        │  │  (Rust binary   │  │
│  │   broker)    │  │   2024.12)  │  │   + embedded    │  │
│  │             │  │             │  │   rumqttd)      │  │
│  │  Port 1883   │  │  Port 8123  │  │  Port 8124      │  │
│  │             │  │  MQTT→1883  │  │  MQTT 1884      │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│         ▲                ▲                ▲              │
│         │                │                │              │
│  ┌──────┴────────────────┴────────────────┴───────────┐  │
│  │              scenario-driver (Python)               │  │
│  │                                                     │  │
│  │  Reads scenario.json                                │  │
│  │  Pushes state to HA via REST (8123)                 │  │
│  │  Pushes state to Marge via REST (8124)              │  │
│  │  Publishes MQTT to both brokers                     │  │
│  │  Manages sim-time                                   │  │
│  │  Supports --speed and --chapter flags               │  │
│  └─────────────────────────────────────────────────────┘  │
│                          ▲                                │
│                          │                                │
│  ┌───────────────────────┴─────────────────────────────┐  │
│  │               dashboard (React, port 3000)           │  │
│  │                                                      │  │
│  │  WebSocket to HA (8123) + Marge (8124)               │  │
│  │  ASCII house visualization                           │  │
│  │  Metrics panel (memory, CPU, latency, events)        │  │
│  │  Timeline bar with chapter markers                   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 4.2 HA Configuration Strategy

HA uses MQTT entities via the MQTT integration. The external Mosquitto broker acts as the bridge. This gives us:
- **Proper entity IDs** (light.bedroom, not input_boolean.bedroom_light)
- **Real service handlers** (light.turn_on publishes to MQTT command topic)
- **Real automation engine** processing real entity state changes
- **MQTT as common protocol** — same as Marge's native backbone

The scenario driver publishes device states to MQTT state topics. HA subscribes and updates entities. HA automations evaluate and fire actions, which publish to MQTT command topics. A **command bridge** (part of the scenario driver) subscribes to command topics and publishes the resulting state updates back, closing the loop.

### 4.3 Marge Architecture (Demo Subset)

```
marge-core/
├── Cargo.toml
├── src/
│   ├── main.rs                 # Tokio runtime, startup sequence
│   ├── mqtt/
│   │   └── broker.rs           # Embedded rumqttd
│   ├── core/
│   │   ├── state.rs            # DashMap<EntityId, EntityState>
│   │   ├── event_bus.rs        # tokio::broadcast channels
│   │   └── automation.rs       # Trigger/condition/action engine
│   ├── api/
│   │   ├── rest.rs             # axum REST handlers
│   │   ├── ws.rs               # WebSocket event stream
│   │   └── health.rs           # /api/health + /api/metrics
│   ├── config/
│   │   └── yaml.rs             # Parse automations.yaml (subset)
│   └── sim/
│       └── time.rs             # Sim-time management for demo
```

**What we implement:**
- Embedded MQTT broker (rumqttd)
- State machine (DashMap + broadcast channel)
- REST API: GET/POST /api/states, GET /api/health, POST /api/sim/time
- WebSocket: subscribe_events for state_changed
- Automation engine: state triggers, time triggers, sun triggers, state conditions, service call actions
- YAML parser: 6 specific automations + 2 scene definitions
- Metrics: RSS from /proc/self/status, event counters, latency tracking

**What we skip (with eyes open):**
- gRPC integration framework
- Go SDK
- HA Python shim
- Entity/Device Registry persistence
- Recorder/History
- Template engine (Jinja2)
- Blueprint system
- OAuth/auth (demo uses no auth)
- Config validation
- Energy management
- Most of the 30+ entity domains (we need: light, switch, sensor, binary_sensor, climate, lock, media_player, alarm_control_panel, scene, button, weather, device_tracker)

---

## 5. THE ASCII HOUSE VISUALIZATION

### 5.1 Interface Contract

```typescript
// This is the ONLY interface the visualization consumes.
// Swap ASCII for Rive by implementing the same contract.
interface HouseView {
  onEntityUpdate(entityId: string, state: string, attributes: Record<string, any>): void;
  onSimTimeUpdate(simTime: Date, speedMultiplier: number): void;
  onSystemStatus(system: "ha" | "marge", status: "online" | "offline" | "starting"): void;
}
```

### 5.2 ASCII Rendering Rules

```
ENTITY TYPE     OFF STATE           ON STATE
─────────────────────────────────────────────────
Light           ○ (dim gray)        ● (bright yellow/amber)
                                    Brightness shown as bar: ████░░░░
Switch          [ OFF ]             [ ON  ] (green)
Lock            🔓 UNLOCKED (red)   🔒 LOCKED (green)
Motion          · (gray)            ◆ (flashing cyan)
Door contact    ═══ (closed)        ═ ═ (open, red)
Temperature     72.1°F (white)      Updates in-place
Alarm           ● DISARMED (gray)   ● ARMED_HOME (green)
                                    ● ARMED_AWAY (blue)
                                    ● ARMED_NIGHT (purple)
                                    ◆ TRIGGERED (flashing red)
Media player    ▷ OFF               ▶ PLAYING (green)
Coffee maker    ○ OFF               ☕ BREWING (brown/yellow)
Smoke/CO        · (gray)            ◆ ALERT (flashing red)
```

Colors via ANSI escape codes (or CSS classes in the React version):
- Yellow (#FFD700): lights on
- Green (#00FF00): locked, armed, on states
- Red (#FF0000): unlocked, alert, open
- Cyan (#00FFFF): motion detected
- Gray (#555555): inactive/off
- White (#FFFFFF): sensor readings
- Purple (#9B59B6): armed_night

### 5.3 Layout

```
┌─ MARGE — Day in the Life ── 05:30:00 ── [▶▶ 10x] ── Chapter: Dawn ─┐
│                                                                       │
│  ┌─ BEDROOM ──────┐ ┌─ BATHROOM ─────┐ ┌─ KITCHEN ──────────────┐   │
│  │ ● ████░░ 20%   │ │ ○              │ │ ○                      │   │
│  │ 🌡 70.0°F       │ │ 🌡 68.2°F       │ │ 🌡 69.5°F  💧 45%      │   │
│  │ · no motion    │ │ 💧 52%          │ │ ☕ BREWING             │   │
│  │ 💧 48%          │ │                │ │ · no motion           │   │
│  └────────────────┘ └────────────────┘ └────────────────────────┘   │
│  ┌─ ENTRYWAY ─────┐                    ┌─ LIVING ROOM ──────────┐   │
│  │ 🔒 LOCKED       │                    │ ○ Main   ○ Accent     │   │
│  │ 🔒 LOCKED       │                    │ ○ Lamp   ○ Floor      │   │
│  │ · no motion    │                    │ ▷ OFF                  │   │
│  │ ═══ closed     │                    │ 🌡 69.8°F  💧 46%      │   │
│  │ ═══ closed     │                    │ · no motion           │   │
│  │ 🌡 68.0°F       │                    └────────────────────────┘   │
│  └────────────────┘                                                  │
│  ┌─ EXTERIOR ──────────────────────────────────────────────────┐     │
│  │ ○ Porch  ○ Path   ● ARMED_HOME   ☀️ Rise 06:47 Set 17:32  │     │
│  │ 🌡 42.1°F 💧 78%   ⚡ 487W  120V  4.1A   🔥· 🏠 home       │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                       │
├─ METRICS ── HA-legacy ─────────────── vs ── Marge ──────────────────┤
│                                                                       │
│  Memory:    782 MB  ████████████████░     14 MB  █░░░░░░░░░░░░░░░   │
│  CPU:       12.3%   ██░░░░░░░░░░░░░░     1.2%   ░░░░░░░░░░░░░░░░   │
│  Events:    1,247                        1,247                       │
│  Latency:   23ms    p99: 147ms           0.08ms  p99: 0.4ms         │
│  Startup:   94s                          0.4s                        │
│  Uptime:    2h 14m                       2h 14m                      │
│                                                                       │
├─ TIMELINE ──────────────────────────────────────────────────────────┤
│  05:00    06:00    12:00    17:00    22:00    03:00                  │
│  ──●────────────────────────────────────────────────── ▶             │
│    ↑dawn                                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. DAY-BY-DAY PLAN

### Day 1: Foundations + HA Baseline

**Morning (4 hours):**

| # | Task | Definition of Done | Risk |
|---|---|---|---|
| 1.1 | Docker compose: mosquitto + HA + placeholder marge | `docker compose up` starts all 3 containers | Low |
| 1.2 | HA `configuration.yaml` with MQTT entities | HA starts, all 43 entities appear in developer tools | Med — MQTT entity YAML is verbose but well-documented |
| 1.3 | HA `automations.yaml` with 6 automations | Automations visible in HA UI | Low |
| 1.4 | HA `scenes.yaml` with 2 scene definitions | Scenes visible in HA UI | Low |
| 1.5 | Command bridge script (Python) | Subscribes to MQTT command topics, publishes state results back | Low |
| 1.6 | Scenario driver MVP (Python) | `python driver.py --target ha --speed 1 --chapter dawn` pushes events to HA | Med |
| 1.7 | **GATE: Dawn chapter runs against HA** | Morning automation fires. Bedroom light turns on. Thermostat changes. Coffee maker on. All verifiable in HA UI. | Critical |

**Afternoon (4 hours):**

| # | Task | Definition of Done | Risk |
|---|---|---|---|
| 1.8 | `cargo new marge-core`, dependencies, module scaffold | `cargo build` succeeds | Low |
| 1.9 | Embedded rumqttd broker starts | MQTT client can connect to port 1884 | Med — rumqttd API |
| 1.10 | Axum HTTP server scaffold | `curl http://localhost:8124/api/` returns 200 | Low |
| 1.11 | **GATE: Marge container builds and starts** | Docker build succeeds. Container stays up. Healthcheck passes. | |

**Fallback for 1.9:** If rumqttd embedded broker fights us, use tokio::broadcast channels internally and skip external MQTT for Marge. The scenario driver talks to Marge via REST API only. Marge's internal event bus still works; it's just not MQTT-backed yet.

### Day 2: Marge Gets a Brain (AI Day — Ralph Loop)

The scenario driver is the test harness. Each checkpoint below is verified by running a chapter of the scenario against Marge and checking the results via curl.

| # | Task | Test | Est. Hours |
|---|---|---|---|
| 2.1 | State machine (DashMap + REST) | `curl POST /api/states/light.kitchen` → `curl GET` returns it | 1.5 |
| 2.2 | Event bus (broadcast channel) | State changes fire events. Internal subscriber logs them. | 1 |
| 2.3 | WebSocket subscribe_events | wscat connects, receives state_changed when curl sets state | 1 |
| 2.4 | Automation engine: YAML parsing | Parse the 6 automations from file. Log parsed structure. | 1 |
| 2.5 | Automation engine: state triggers | Set `binary_sensor.entryway_motion` to `on` → automation evaluates | 1.5 |
| 2.6 | Automation engine: state conditions | Security automation checks alarm_control_panel state | 0.5 |
| 2.7 | Automation engine: service call actions | Automation fires `light.turn_on` → state machine updates light | 1.5 |
| 2.8 | Sim-time endpoint + time triggers | `POST /api/sim/time {"time":"05:30"}` → morning automation fires | 1 |
| 2.9 | Sun triggers (hardcoded sunrise/sunset) | Sunset event → exterior lights + scene | 0.5 |
| 2.10 | Scene support (batch state update) | scene.turn_on sets all 5 entities | 0.5 |
| 2.11 | Health/metrics endpoint | `curl /api/health` returns RSS, events, latency | 1 |
| 2.12 | **GATE: Full scenario against Marge** | All 6 automations fire correctly. State matches HA baseline. | |

**Total estimate: ~11 hours.** This is tight for one day. Mitigation:

- **If YAML parsing is hard:** Hardcode the 6 automations as Rust structs. Be honest in the demo ("YAML parser is Phase 2, but the engine evaluates identically"). This saves 1-2 hours.
- **If conditions/actions are hard:** Implement just state trigger + service call action (no conditions). Security automation becomes unconditional. Still demonstrates the architecture.
- **If everything goes sideways:** A Marge that accepts state via REST, stores it, serves it via WebSocket, and reports metrics is STILL a valid demo of the state machine + MQTT broker. The automation engine is a bonus.

### Day 3: Dashboard

| # | Task | Definition of Done | Est. Hours |
|---|---|---|---|
| 3.1 | Vite + React + Tailwind scaffold | `npm run dev` serves empty page | 0.5 |
| 3.2 | WebSocket client to both HA and Marge | Console.log shows events from both | 1 |
| 3.3 | ASCII house component | Renders floor plan from entity state map | 2 |
| 3.4 | Entity state coloring and icons | Lights glow, locks show green/red, motion flashes | 1 |
| 3.5 | Metrics panel | Side-by-side bars for memory, CPU, events, latency | 1.5 |
| 3.6 | Timeline bar | Shows sim-time, speed, chapter markers | 1 |
| 3.7 | System status (online/offline/starting) | Shows system going down/up during outage | 0.5 |
| 3.8 | **GATE: Full run-through with dashboard** | Scenario plays. House animates. Metrics show the gap. | |

### Day 4: Polish + Demo Prep

| # | Task | Est. Hours |
|---|---|---|
| 4.1 | Power outage sequence: `docker stop` + `docker start` both containers, dashboard shows the gap, measures recovery time | 2 |
| 4.2 | Score card overlay: summary table at end with key metrics | 1 |
| 4.3 | Demo flow script: write down what to say at each chapter | 1 |
| 4.4 | Rehearsal run-throughs (at least 2) | 2 |
| 4.5 | Bug fixes from rehearsal | 2 |
| 4.6 | **Bonus if time:** Rive house animation via same HouseView interface | Stretch |
| 4.7 | **Bonus if time:** Structured JSON log stream panel | Stretch |

---

## 7. CONFIDENCE MATRIX

| Component | Confidence | Impact if Missing | Notes |
|---|---|---|---|
| HA + MQTT entities + automations | 90% | Fatal — no baseline | Well-documented, battle-tested |
| Scenario driver | 95% | Fatal — no events | Simple Python script |
| Marge state machine + REST | 90% | Fatal — no Marge | ~300 lines of known Rust patterns |
| Marge embedded MQTT | 75% | Degraded — REST only | Fallback to in-memory channels |
| Marge automation engine | 70% | Degraded — no auto-response | Can hardcode 6 rules as plan B |
| Marge YAML parsing | 60% | Cosmetic — hardcode instead | miniserde or serde_yaml |
| ASCII dashboard | 90% | Degraded — curl only | Standard React |
| Metrics panel | 85% | Degraded — less visual impact | /proc/self/status is trivial |
| Power outage sequence | 75% | Degraded — show numbers separately | Docker restart is scriptable |
| **Full demo as described** | **75%** | | **Even degraded version is a strong demo** |

---

## 8. THE THIRD AGENDA

Notes for the demo presentation (what you're actually saying):

1. **"This is a personal side project."** Let that sink in. One person. Four days. With AI.

2. **"The functional behavior is identical."** Same events. Same automations. Same outcomes. The CTS guarantees it. Point at the house — it's doing the same thing on both sides.

3. **"The operational profile is not."** Point at the metrics. 14 MB vs 800 MB. Sub-millisecond latency vs double-digit milliseconds. 0.4 second startup vs 90+ seconds. These aren't estimates — they're measured in real time right in front of you.

4. **"The hard part wasn't writing code."** The hard part was writing a spec rigorous enough that an AI could iterate against it. The CTS is 1,200 tests. The SSS is MIL-STD-498 format. The TheoryOps covers 7 failure classes. THAT's where the engineering went. The Rust came from an LLM that could verify its own work.

5. **"Now imagine applying this to what we ship."** Don't spell it out. Let them fill in the gap.

---

## 9. FILES IN THIS PACKAGE

| File | Purpose |
|---|---|
| `demo-plan.md` | This document |
| `scenario.json` | Complete event timeline for all 8 chapters |
| `docker-compose.yml` | Container orchestration |
| `ha-config/configuration.yaml` | HA entity declarations (MQTT) |
| `ha-config/automations.yaml` | 6 automation definitions |
| `ha-config/scenes.yaml` | 2 scene definitions |
