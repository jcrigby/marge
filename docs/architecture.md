# MARGE — Architecture

**Document Number:** MRG-ARCH-001
**Version:** 1.0
**Date:** 2026-02-16
**Parent Documents:** MRG-SSS-001 (System Spec), MRG-OPS-001 (Theory of Operations)

---

## 1. OVERVIEW

Marge is a clean-room reimplementation of Home Assistant's core automation platform in Rust. It provides HA-compatible REST, WebSocket, and MQTT APIs so that existing tools, dashboards, and device bridges (zigbee2mqtt, zwave-js-ui, etc.) work without modification.

The system is a single statically-linked binary (~90 MB Docker image) that embeds its own MQTT broker, HTTP server, WebSocket server, SQLite database, template engine, automation runtime, and WASM plugin host. There are no external dependencies at runtime except the filesystem.

### 1.1 Key Numbers

| Metric | Value |
|---|---|
| Rust core | 11,958 lines across 19 source files |
| React dashboard | 8,982 lines across 19 components |
| CTS tests | 4,854 tests across 413 pytest files |
| Integrations | 7 (zigbee2mqtt, zwave, tasmota, esphome, weather, shelly, hue) |
| Domains | 40 entity domains, 119 services |
| Memory (RSS) | ~12 MB baseline, ~150 MB under CTS load |
| Cold startup | <1 ms |
| Commits | 269 |

---

## 2. SYSTEM ARCHITECTURE

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    marge binary                         │
                    │                                                         │
  HTTP :8124 ──────►│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐  │
                    │  │  axum    │    │  Automation   │    │   WASM       │  │
  WS /api/ws ──────►│  │  Router  │    │  Engine       │    │   Plugin     │  │
                    │  │  (api.rs)│    │  (automation  │    │   Runtime    │  │
                    │  │          │    │   .rs)        │    │  (plugins.rs)│  │
                    │  └────┬─────┘    └──────┬───────┘    └──────┬───────┘  │
                    │       │                 │                    │          │
                    │       ▼                 ▼                    ▼          │
                    │  ┌──────────────────────────────────────────────────┐   │
                    │  │              AppState (state.rs)                 │   │
                    │  │  ┌────────────────┐  ┌────────────────────────┐ │   │
                    │  │  │ DashMap<String, │  │ tokio::broadcast      │ │   │
                    │  │  │  EntityState>   │  │ (state change events) │ │   │
                    │  │  └────────────────┘  └────────────────────────┘ │   │
                    │  └──────────────────────────────────────────────────┘   │
                    │       │                 │                    │          │
                    │       ▼                 ▼                    ▼          │
                    │  ┌──────────┐    ┌──────────────┐    ┌──────────────┐  │
                    │  │ Recorder │    │   Service     │    │  Template    │  │
                    │  │ (SQLite) │    │   Registry    │    │  Engine      │  │
                    │  │          │    │  (services.rs)│    │  (minijinja) │  │
                    │  └──────────┘    └──────────────┘    └──────────────┘  │
                    │       │                                                 │
                    │       ▼                                                 │
                    │  ┌──────────────────────────────────────────────────┐   │
                    │  │           Embedded MQTT Broker (rumqttd)         │   │
                    │  │                    :1884                          │   │
                    │  └──────────────────────────────────────────────────┘   │
                    │       │                                                 │
                    └───────┼─────────────────────────────────────────────────┘
                            │
              ┌─────────────┼──────────────────────────────────┐
              ▼             ▼                ▼                  ▼
      ┌─────────────┐ ┌──────────┐  ┌────────────┐    ┌──────────────┐
      │ zigbee2mqtt │ │ zwave-js │  │  Tasmota/   │    │   Shelly/    │
      │  (bridge)   │ │   -ui    │  │  ESPHome    │    │   Hue        │
      │             │ │          │  │  (MQTT)     │    │   (HTTP)     │
      └─────────────┘ └──────────┘  └────────────┘    └──────────────┘
```

---

## 3. CORE MODULES

### 3.1 HTTP API — `api.rs` (2,346 lines)

The axum 0.7 router. All HA-compatible endpoints plus Marge extensions.

**HA-compatible endpoints:**
- `GET /api/` — API status
- `GET /api/config` — system configuration
- `GET /api/states` — all entity states
- `GET/POST /api/states/:entity_id` — get/set individual entity
- `POST /api/services/:domain/:service` — call a service
- `POST /api/events/:event_type` — fire an event
- `GET /api/history/period/:timestamp` — historical state data
- `GET /api/logbook/:timestamp` — logbook entries
- `GET /api/error_log` — error log
- `POST /api/template` — render a Jinja2 template

**Marge extensions:**
- `GET /api/health` — health check with uptime and entity count
- `GET /api/integrations` — list all integrations with status
- `GET/POST /api/integrations/{shelly,hue,zigbee2mqtt,zwave,tasmota,esphome}` — per-integration management
- `POST /api/auth/login` — user authentication
- `GET/POST/DELETE /api/auth/users` — user management
- `GET /api/backup` — download tar.gz backup
- `POST /api/restore` — upload tar.gz to restore
- `GET/POST/PUT/DELETE /api/automations` — automation CRUD
- `POST /api/config/sim_time` — simulation time control (for testing)

**Authentication:** Bearer token in `Authorization` header. Tokens are either long-lived (stored in SQLite) or session tokens from `/api/auth/login`. The `check_auth()` function validates on every request.

**Routing note:** axum 0.7.x uses `:param` syntax. axum 0.8+ uses `{param}`. This matters if upgrading.

### 3.2 State Machine — `state.rs` (169 lines)

The central entity store. Deceptively simple — it's a `DashMap<String, EntityState>` (lock-free concurrent hashmap) plus a `tokio::broadcast::Sender` for change notifications.

```rust
pub struct StateMachine {
    states: DashMap<String, EntityState>,
    tx: broadcast::Sender<StateChangeEvent>,
}
```

Every component that needs entity state reads from the DashMap. Every component that needs to react to changes subscribes to the broadcast channel. This is the spine of the system — the automation engine, WebSocket event stream, recorder, and integrations all hang off this single pub/sub mechanism.

`EntityState` holds: `entity_id`, `state` (string), `attributes` (JSON map), `last_changed`, `last_updated`.

### 3.3 Automation Engine — `automation.rs` (1,220 lines)

Parses HA-format `automations.yaml` and evaluates trigger/condition/action pipelines.

**Triggers supported:**
- `state` — entity state changes (with optional `from`/`to` filters)
- `time` — wall clock or sim-time match (`at: "HH:MM:SS"`)
- `sun` — sunrise/sunset with offset (NOAA solar algorithm)

**Conditions:** `state`, `numeric_state`, `time`, `template` (Jinja2 expression)

**Actions:** `service` calls, `delay`, `wait_template`, `choose` (if/else), `repeat` (count/while/until), `parallel` (concurrent execution), `event` (fire custom event)

**Run modes:** `single`, `parallel`, `queued`, `restart` — controls what happens when an automation triggers while already running.

**Execution model:** Automations are stored in an `Arc<RwLock<Vec<Automation>>>` for hot-reload. A background `run_time_loop` task polls time/sun triggers every 500ms. State triggers fire synchronously from the broadcast channel. Deduplication via `last_time_triggers` DashMap prevents re-firing within the same second.

### 3.4 MQTT Broker — `mqtt.rs` (229 lines)

Embeds rumqttd 0.19 as an in-process MQTT broker on port 1884. This means Marge doesn't need an external Mosquitto — devices can publish directly to Marge.

The `MqttSubscriber` connects as an internal client and routes messages to:
1. **MQTT Discovery** (`homeassistant/+/+/config`) — auto-creates entities
2. **Integration bridges** — zigbee2mqtt, zwave, tasmota, esphome topic handlers
3. **State updates** — entity state_topic subscriptions from discovery

**Critical implementation note:** `broker.start()` is blocking. It runs in a `spawn_blocking` task to avoid stalling the tokio runtime.

### 3.5 MQTT Discovery — `discovery.rs` (832 lines)

Implements the HA MQTT Discovery protocol. Any device or bridge that publishes to `homeassistant/<component>/<node_id>/config` gets an entity created automatically.

**Supported component types:** sensor, binary_sensor, light, switch, climate, cover, fan, lock, alarm_control_panel, number, select, button, text, scene, siren, vacuum, event, valve, update, device_tracker, humidifier, lawn_mower, camera, remote, water_heater (~25 types).

**Per-entity wiring:**
- Subscribe to `state_topic` for state updates
- Subscribe to `availability_topic` for online/offline
- Apply `value_template` (Jinja2) to extract state from JSON payloads
- Register `command_topic` for outbound commands when services are called

**Entity removal:** Empty payload on the config topic deletes the entity (HA convention).

### 3.6 Service Registry — `services.rs` (988 lines)

Dynamic service dispatch. Maps `(domain, service)` pairs to handler functions.

**40 domains** registered at startup: light, switch, lock, climate, cover, fan, alarm_control_panel, media_player, vacuum, siren, number, select, button, humidifier, water_heater, lawn_mower, camera, remote, device_tracker, valve, and 20 more.

**119 services** total, including: turn_on, turn_off, toggle, set_temperature, set_hvac_mode, open_cover, close_cover, lock, unlock, set_value, play_media, volume_set, etc.

Services that target MQTT-discovered entities publish to the entity's `command_topic`. Services targeting Shelly/Hue devices dispatch to the appropriate HTTP API.

### 3.7 Recorder — `recorder.rs` (873 lines)

SQLite with WAL mode for crash-safe persistence.

**Tables:**
- `states` — entity state history (entity_id, state, attributes JSON, timestamp)
- `events` — event log (event_type, data JSON, timestamp)
- `tokens` — long-lived access tokens
- `users` — local user accounts (username, argon2id password hash)
- `automations` — automation metadata (trigger counts, last triggered)

**Write batching:** State changes are coalesced with 100ms batching to avoid write amplification. History queries support time-range filtering and entity filtering.

**Retention:** Configurable auto-purge (default 10 days). Statistics aggregation for hourly/daily rollups.

### 3.8 Template Engine — `template.rs` (506 lines)

Wraps minijinja to provide HA-compatible Jinja2 template rendering.

**Filters:** `upper`, `lower`, `trim`, `replace`, `abs`, `log`, `round`, `int`, `float`, `max`, `min`, `from_json`, `to_json`, `iif`, `is_defined`, `default`, `timestamp_local`, `as_datetime`

**Global functions:** `states(entity_id)`, `is_state(entity_id, value)`, `state_attr(entity_id, attr)`, `now()`, `float(value)`, `int(value)`, `bool(value)`

**Used by:** Discovery value_templates, automation conditions, automation action data templates, REST API `/api/template` endpoint.

### 3.9 WebSocket — `websocket.rs` (554 lines)

HA-compatible WebSocket API at `/api/websocket`.

**Protocol:** Connect, receive `auth_required`, send `auth` with `access_token`, receive `auth_ok`. Then send commands with incrementing `id` fields.

**Commands:** `subscribe_events`, `unsubscribe_events`, `get_states`, `get_config`, `get_services`, `get_panels`, `ping`, `call_service`, `fire_event`, `subscribe_trigger`, `render_template`, `search/related`, `get_areas`, `create_area`, `update_area`, `delete_area`, `get_devices`, `get_labels`, `create_label`, `update_label`, `delete_label`, `logbook/get_events`, `execute_script` (23 command types).

**Event delivery:** Subscribed clients receive `state_changed` events via the broadcast channel. Each connection runs its own forwarding task.

### 3.10 Authentication — `auth.rs` (236 lines)

- **Password hashing:** argon2id via the `argon2` crate with random salt
- **Token validation:** checks `Authorization: Bearer <token>` against SQLite tokens table
- **Login flow:** POST `/api/auth/login` with username/password, returns session token
- **Default bootstrap:** On first startup, creates `admin`/`admin` account if no users exist

---

## 4. INTEGRATION ARCHITECTURE

Integrations fall into three tiers based on how they connect to devices.

### 4.1 Tier 1: MQTT Bridge Integrations

These integrate with external MQTT bridges that manage their own device networks. Marge subscribes to their topic trees and creates/updates entities from the messages.

| Integration | File | Lines | Protocol |
|---|---|---|---|
| zigbee2mqtt | `integrations/zigbee2mqtt.rs` | 417 | MQTT topics: `zigbee2mqtt/#` |
| zwave-js-ui | `integrations/zwave.rs` | 302 | MQTT topics: `zwave/#` |
| Tasmota | `integrations/tasmota.rs` | 344 | MQTT topics: `stat/`, `tele/`, `cmnd/` |
| ESPHome | `integrations/esphome.rs` | 270 | MQTT topics: `<prefix>/<component>/<name>/state` |

These integrations also benefit from MQTT Discovery — they publish `homeassistant/` config topics, so basic entity creation happens automatically via `discovery.rs`. The dedicated bridge modules add deeper management: device registries, pairing flows, bridge health monitoring.

### 4.2 Tier 2: HTTP Polling Integrations

These talk directly to devices or bridges over HTTP. They run background polling loops and create entities from the responses.

| Integration | File | Lines | Protocol |
|---|---|---|---|
| Shelly | `integrations/shelly.rs` | 694 | Gen1: REST (`/status`, `/relay/N`). Gen2: JSON-RPC (`/rpc/Switch.Set`) |
| Philips Hue | `integrations/hue.rs` | 676 | Hue Bridge REST API (`/api/{user}/lights`, `/sensors`) |
| Weather | `integrations/weather.rs` | 212 | Met.no REST API (30-min poll interval) |

Each HTTP integration follows the same pattern:
1. A struct wrapping `DashMap` (device registry) + `Arc<AppState>` + `reqwest::Client`
2. A polling function that fetches device state and calls `app_state.state_machine.set()`
3. A `start_*_poller()` function that spawns a tokio task with a fixed interval
4. REST endpoints in `api.rs` for status and management

### 4.3 Tier 3: WASM Plugins

For cloud integrations that only need periodic HTTP calls (weather services, cloud device APIs, notification services), Marge provides a sandboxed WASM plugin runtime.

See Section 5 for details.

### 4.4 Adding a New Integration

Every integration follows this pattern:

1. Create `marge-core/src/integrations/<name>.rs`
2. Add `pub mod <name>;` to `integrations/mod.rs`
3. Create the bridge/integration struct and polling loop
4. Add API endpoints to `api.rs` (status + management)
5. Wire into `main.rs` (create instance, start poller, pass to router)
6. Add UI component to `IntegrationManager.tsx`
7. Write CTS tests in `tests/test_<name>.py`

---

## 5. WASM PLUGIN SYSTEM

### 5.1 Purpose

The WASM plugin system (`plugins.rs`, 595 lines) exists to handle the long tail of cloud integrations — the hundreds of REST API services (Tuya, TP-Link, Spotify, Telegram, etc.) that don't justify compiled Rust modules but need more isolation than "just add another HTTP poller."

It is NOT for local device integrations. Shelly, Hue, and similar integrations that need persistent connections, mDNS discovery, or real-time event streams are Rust core modules (Tier 2).

### 5.2 Runtime

**Engine:** Wasmtime v29, the industry-standard WASM runtime (also used by Envoy, Cloudflare, Shopify).

**Sandboxing:** Each plugin runs in its own `Store` with isolated linear memory. A plugin cannot access the filesystem, network, or other plugins' memory directly — it can only interact with the outside world through host functions.

**Fuel metering:** Each invocation gets a budget of 1,000,000 fuel units. Infinite loops or excessive computation exhaust the fuel and trap cleanly. This prevents a misbehaving plugin from blocking the system.

**Plugin loading:** On startup, Marge scans `/config/plugins/` for `.wasm` files, compiles each with Wasmtime, and calls the `init()` export if present.

### 5.3 Host Functions

Plugins import functions from the `"env"` module:

| Function | Signature | Purpose |
|---|---|---|
| `marge_log` | `(level: i32, msg_ptr: i32, msg_len: i32)` | Log a message (0=error, 1=warn, 2=info, 3=debug) |
| `marge_get_state` | `(entity_ptr: i32, entity_len: i32) -> i32` | Look up entity state (returns JSON length) |
| `marge_set_state` | `(entity_ptr: i32, entity_len: i32, state_ptr: i32, state_len: i32)` | Set an entity's state value |
| `marge_http_get` | `(url_ptr: i32, url_len: i32, buf_ptr: i32, buf_len: i32) -> i64` | HTTP GET, write response to buffer |
| `marge_http_post` | `(url_ptr: i32, url_len: i32, body_ptr: i32, body_len: i32, buf_ptr: i32, buf_len: i32) -> i64` | HTTP POST with body |

**HTTP return value:** Packed i64 — high 32 bits = HTTP status code (or -1 on error), low 32 bits = bytes written to the response buffer.

**Async bridging:** Host HTTP functions use `tokio::task::block_in_place` + `Handle::block_on` to call async reqwest from within synchronous WASM host functions. The reqwest client has a 10-second timeout.

### 5.4 Plugin Exports

Plugins must export:
- `fn init()` — called once on load
- `fn on_state_changed(entity_ptr, entity_len, old_ptr, old_len, new_ptr, new_len)` — called on entity state changes (optional)

### 5.5 What Languages Can Plugins Be Written In?

WASM is a compilation target. Plugin authors write in a source language and compile to `.wasm`:

- **Rust** — best support, smallest binaries. `cargo build --target wasm32-wasi`
- **AssemblyScript** — TypeScript-like syntax, easy for web developers. Likely the community sweet spot.
- **C/C++** — via Emscripten or clang `--target=wasm32-wasi`
- **Go** — via TinyGo (standard Go produces large binaries)
- **JavaScript** — via QuickJS-to-WASM (e.g., Javy)

Marge doesn't care what produced the `.wasm` file. The binary format is language-agnostic.

### 5.6 Why WASM Instead of Python/Lua/JavaScript?

Home Assistant's integration model is "load arbitrary Python into the core process." This means:
- No isolation — a bad integration can deadlock the event loop or corrupt memory
- No resource limits — a polling loop that leaks 50 MB affects the whole system
- Dependency hell — conflicting package versions across integrations
- Security — full filesystem and network access by default

WASM solves all of these by design: memory isolation per plugin, fuel-metered execution, explicit capability grants (a plugin can only do what the host functions allow), and language-agnostic distribution.

The tradeoff is higher friction for plugin authors. This is intentional — a home automation system should prioritize reliability over developer convenience.

---

## 6. DATA FLOW

### 6.1 Device State Change (MQTT path)

```
Device (e.g., Zigbee sensor)
  → zigbee2mqtt bridge
    → MQTT publish to zigbee2mqtt/<name>
      → rumqttd broker (port 1884)
        → MqttSubscriber receives message
          → zigbee2mqtt.rs parses JSON payload
            → state_machine.set(entity_id, state, attributes)
              → broadcast::Sender sends StateChangeEvent
                → WebSocket subscribers get event pushed
                → Automation engine evaluates state triggers
                → Recorder batches write to SQLite
```

### 6.2 Device State Change (HTTP path)

```
Device (e.g., Shelly relay)
  → shelly.rs poller (every 10s)
    → HTTP GET /status (Gen1) or /rpc/Shelly.GetStatus (Gen2)
      → Parse response JSON
        → state_machine.set(entity_id, state, attributes)
          → (same broadcast chain as above)
```

### 6.3 Service Call (user turns on a light)

```
User clicks button in UI
  → React sends POST /api/services/light/turn_on {entity_id: "light.kitchen"}
    → api.rs routes to service registry
      → services.rs looks up (light, turn_on) handler
        → Handler determines entity's integration:
          - MQTT-discovered: publish to command_topic
          - Shelly: HTTP POST /relay/0?turn=on or /rpc/Switch.Set
          - Hue: HTTP PUT /api/{user}/lights/{id}/state
        → Response: updated entity state
```

### 6.4 Automation Execution

```
State change event fires
  → automation.rs evaluates all automations' trigger lists
    → Match found: automation "evening_lights"
      → Evaluate conditions (template, state, time checks)
        → All pass: execute action sequence
          → action: call_service(light, turn_on, {brightness: 200})
            → service registry dispatches
          → action: delay(5 seconds)
          → action: call_service(scene, turn_on, {entity_id: scene.evening})
            → scene.rs applies batch state changes
```

---

## 7. FRONTEND

### 7.1 React Dashboard — `marge-ui/` (8,982 lines)

Single-page React 19 + TypeScript application built with Vite. Served by Marge itself via tower-http `ServeDir` (no separate web server needed).

**8 tabs:**
1. **Entities** — sortable/filterable entity list with domain-specific cards
2. **Automations** — list with trigger counts, last-triggered time, enable/disable toggle
3. **Scenes** — scene activation buttons
4. **Areas** — area management (create, rename, delete, assign entities)
5. **Devices & Labels** — device registry and label management
6. **Integrations** — per-integration status cards with management UIs
7. **Logs** — real-time event stream and error log
8. **Settings** — system info, API token management, sim-time control

**Real-time updates:** WebSocket connection (`ws.ts`) subscribes to `state_changed` events. Entity cards update immediately when state changes.

**Authentication:** Login page (`LoginPage.tsx`) gates the app. Session token stored in localStorage. Logout button in header.

**Responsive:** Tablet and mobile breakpoints in `App.css`.

### 7.2 Integration Management UIs

Each Tier 2+ integration has a dedicated view in `IntegrationManager.tsx`:
- **Shelly:** Device table (IP, MAC, type, gen, firmware, online status) + manual IP discovery
- **Hue:** Bridge cards (name, model, firmware) + link-button pairing flow + device tables
- **zigbee2mqtt:** Device list + permit-join toggle for pairing
- **zwave/tasmota/esphome:** Device lists with bridge status

---

## 8. TESTING

### 8.1 Conformance Test Suite (CTS)

The CTS (`tests/`, 4,854 tests, 73,440 lines of Python) validates HA API compatibility. Tests run against a live Marge instance using pytest + httpx + websockets + paho-mqtt.

**Test categories:**
- Core API: states, services, events, config, health (~500 tests)
- Entity domains: all 40 domains with lifecycle tests (~170 tests)
- Automation: trigger/condition/action combinations (~75 tests)
- WebSocket: all 23 command types
- MQTT Discovery: sensor, binary_sensor, light, switch, climate, cover, lock + value_template
- History/logbook: time-range queries, entity filtering, statistics
- Auth: login, tokens, user management
- Template: filters, globals, edge cases
- Integration endpoints: Shelly, Hue, bridge status
- Performance: memory thresholds, concurrent connections, rapid state changes

### 8.2 Rust Unit Tests

63 unit tests embedded in source files (`#[cfg(test)]` modules). Cover:
- Template rendering and filters
- Discovery payload parsing
- Integration device/entity creation
- Service registry dispatch
- Bridge state management

### 8.3 Running Tests

```bash
# Rust unit tests
cd marge-core && cargo test

# CTS (requires running Marge instance on :8124)
cd tests && pip install -r requirements.txt && pytest --tb=short -q

# React build verification
cd marge-ui && npx vite build
```

---

## 9. DEPLOYMENT

### 9.1 Docker

```dockerfile
# Two-stage build: React UI + Rust binary
FROM node:20-slim AS ui-builder    # Build React
FROM rust:1.93-slim-bookworm AS builder  # Build Rust
FROM debian:bookworm-slim AS runtime     # ~90 MB final image
```

```bash
docker compose up -d    # Starts marge on :8124, MQTT on :1884
```

### 9.2 Configuration

- `config/automations.yaml` — automation definitions (HA format)
- `config/scenes.yaml` — scene definitions (HA format)
- `config/plugins/` — WASM plugin directory
- Environment variables: `MARGE_PORT`, `MARGE_MQTT_PORT`, `MARGE_DB_PATH`, `MARGE_LOG_LEVEL`

### 9.3 Backup/Restore

- `GET /api/backup` — downloads tar.gz of SQLite database + config files
- `POST /api/restore` — uploads tar.gz, extracts, reloads configuration

---

## 10. DEPENDENCY MAP

| Crate | Version | Purpose |
|---|---|---|
| tokio | 1 | Async runtime |
| axum | 0.7 | HTTP/WebSocket server |
| tower-http | 0.5 | CORS, tracing, static file serving |
| serde / serde_json / serde_yaml | 1 / 1 / 0.9 | Serialization |
| dashmap | 6 | Lock-free concurrent hashmap |
| rumqttd | 0.19 | Embedded MQTT broker |
| rumqttc | 0.24 | MQTT client (for internal subscriber) |
| rusqlite | 0.31 | SQLite (bundled, WAL mode) |
| minijinja | 2 | Jinja2 template engine |
| wasmtime | 29 | WASM plugin runtime |
| reqwest | 0.12 | HTTP client (integrations, plugins) |
| argon2 | 0.5 | Password hashing |
| chrono | 0.4 | Date/time handling |
| uuid | 1 | Unique ID generation |
| tar / flate2 | 0.4 / 1 | Backup archive creation |
| tracing / tracing-subscriber | 0.1 / 0.3 | Structured logging |
| anyhow / thiserror | 1 / 1 | Error handling |
