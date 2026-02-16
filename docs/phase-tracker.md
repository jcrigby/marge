# Phase Tracker — Protocol-First HA Replacement

## Goal
Turn Marge from a demo into a real HA replacement covering ~70% of functionality
via protocol-first approach: MQTT Discovery + zigbee2mqtt + zwave-js-ui + ESPHome/Tasmota.

## Phase 1: Foundation — COMPLETE (2026-02-14)
- [x] SQLite + WAL persistence (recorder.rs, 800 LOC)
- [x] MQTT Discovery, 18+ component types (discovery.rs, 830 LOC)
- [x] minijinja template engine, 17 filters + 7 globals (template.rs, 506 LOC)
- [x] Dynamic service registry, 119 services / 40 domains (services.rs, 989 LOC)
- [x] React UI with 7 tabs (marge-ui/, 16 components)
- [x] 3633/3633 CTS green

## Phase 2: Device Bridges — COMPLETE (2026-02-14)
All four bridges implemented with unit tests + CTS integration tests.
- [x] zigbee2mqtt bridge (integrations/zigbee2mqtt.rs, 406 LOC, 5 unit tests)
  - bridge state, device registry, groups, bridge events, permit join, availability
- [x] zwave-js-ui bridge (integrations/zwave.rs, 301 LOC, 4 unit tests)
  - node registry, command class mapping, gateway detection, writeValue, inclusion
- [x] Tasmota bridge (integrations/tasmota.rs, 342 LOC, 5 unit tests)
  - LWT, telemetry, sensor parsing, power states, device info
- [x] ESPHome bridge (integrations/esphome.rs, 268 LOC, 4 unit tests)
  - status, component state, prefix matching, domain mapping
- [x] All wired into mqtt.rs subscriber loop and main.rs

## Phase 3: Automation Engine — COMPLETE (2026-02-14)
- [x] Time triggers: run_time_loop with 500ms poll, sim-time + wall clock
- [x] Sun triggers: NOAA solar algorithm, sunrise/sunset with offset
- [x] Scripts: delay, wait_template, choose, repeat, parallel
- [x] Template conditions and actions via minijinja
- [x] Dedup via last_time_triggers DashMap

## Phase 4: Frontend + Config UI + Auth — COMPLETE (2026-02-14)
- [x] React dashboard with 8 tabs (entities, automations, scenes, areas, devices/labels, integrations, logs, settings)
- [x] Entity cards with sort/filter
- [x] WebSocket real-time updates
- [x] Long-lived access tokens (persisted in SQLite)
- [x] Token-based API auth (auth.rs)
- [x] Integrations REST API (6 endpoints: list + per-bridge status/devices)
- [x] Integrations UI tab (IntegrationManager.tsx, bridge cards, device tables, auto-refresh)
- [x] Responsive mobile layout (tablet + mobile breakpoints in App.css)
- [x] Local user accounts (argon2id hashing, SQLite users table, CRUD API, default admin bootstrap)
- [x] Auth endpoints (login, create/list/delete users)
- [x] Login page UI (LoginPage.tsx, auth gate in App.tsx, logout button)
- [x] Zigbee2mqtt pairing flow (permit_join toggle wired in IntegrationManager)
- [x] Visual automation editor (AutomationEditor.tsx, form-based triggers/conditions/actions, YAML preview)

## Phase 5: Plugin System — MOSTLY COMPLETE (2026-02-14)
- [x] WASM plugin runtime (plugins.rs, 374 LOC, wasmtime v29, fuel metering, host functions)
- [x] Weather integration (integrations/weather.rs, 212 LOC, Met.no API poller, 5 entities)
- [x] Webhook receiver (api.rs, already existed — state set + event fire)
- [ ] Subprocess/sidecar manager (for Matter, cameras) — deferred
- [ ] Additional cloud integrations (Telegram, Spotify) — deferred

## Phase 6: Production Hardening — MOSTLY COMPLETE (2026-02-14)
- [x] Graceful shutdown (SIGTERM/SIGINT signal handling in main.rs)
- [x] History queries + statistics aggregation
- [x] Backup (GET /api/backup — tar.gz of DB + config)
- [x] Restore (POST /api/restore — tar.gz upload, DB + config extraction, auto-reload)
- [ ] Matter support (python-matter-server sidecar) — deferred
- [ ] Mobile companion app — deferred

## Phase 7: Local Network Integrations — IN PROGRESS
**Goal**: Cover the ~15% of homes that use non-MQTT local devices (Shelly, Hue, Sonos, Cast).
These are Rust core modules in `integrations/`, NOT WASM plugins, because they need
persistent connections, mDNS discovery, or event streams.

Priority order (by install base and effort):

### 7.1 Shelly (112K installs) — COMPLETE (2026-02-16)
- [x] Gen1: HTTP REST API (`/status`, `/relay/0?turn=on`)
- [x] Gen2: RPC over HTTP (`/rpc/Shelly.GetStatus`, `/rpc/Switch.Set`, `/rpc/Light.Set`)
- [x] Device discovery via manual IP + GET /shelly probe
- [x] Entities: switch, light, sensor (power/energy/temperature)
- [x] 10s HTTP polling loop
- [x] API: GET /api/integrations/shelly/status, POST /api/integrations/shelly/discover
- [x] UI: ShellyView in IntegrationManager with device table + manual discovery
- **File**: `integrations/shelly.rs` (470 LOC, 7 unit tests)

### 7.2 Philips Hue (76K installs) — COMPLETE (2026-02-16)
- [x] REST API polling: /api/{user}/lights, /api/{user}/sensors, /api/{user}/config
- [x] Link button pairing: POST /api with devicetype, receives username
- [x] Light entities: brightness, color_temp, xy_color, reachable, manufacturer
- [x] Sensor entities: ZLLPresence (motion), ZLLTemperature (1/100 C), ZLLLightLevel (lux), Daylight
- [x] Command dispatch: PUT /api/{user}/lights/{id}/state with on/bri/ct/xy/transitiontime
- [x] 5s polling loop
- [x] API: GET /api/integrations/hue/status, POST pair, POST add
- [x] UI: HueView with bridge cards, pair/add toggle, device tables
- **File**: `integrations/hue.rs` (676 LOC, 7 unit tests)

### 7.3 Google Cast (238K installs) — MEDIUM PRIORITY (hard)
- mDNS discovery (`_googlecast._tcp.local`)
- Castv2 protocol: TLS + Protobuf over TCP
- Media control: play/pause/stop/volume, media_player entity
- **File**: `integrations/cast.rs`, ~800 LOC
- **Deps**: prost (protobuf), tokio-rustls
- **Note**: Hardest integration. Consider deferring or using a Go/Python sidecar.

### 7.4 Sonos (76K installs) — MEDIUM PRIORITY
- SSDP/UPnP discovery
- SOAP API for transport control (play/pause/volume/queue)
- HTTP event subscriptions for state changes
- Entities: media_player (play/pause/volume/source/media_title)
- **File**: `integrations/sonos.rs`, ~500-600 LOC

### 7.5 Matter Sidecar Manager (168K installs) — MEDIUM PRIORITY
- NOT a Rust reimplementation — manage python-matter-server as a subprocess
- JSON-RPC over WebSocket to the sidecar
- Sidecar handles Thread/BLE commissioning, Marge handles entity mapping
- **File**: `integrations/matter.rs` + `sidecar.rs`, ~300-400 LOC
- **Deps**: tokio-tungstenite (already have WS infra)

### 7.6 WASM HTTP Host Functions — COMPLETE (2026-02-16)
- [x] `marge_http_get(url_ptr, url_len, buf_ptr, buf_len) -> i64` (packed status|body_len)
- [x] `marge_http_post(url_ptr, url_len, body_ptr, body_len, buf_ptr, buf_len) -> i64`
- [x] Bridges async reqwest into synchronous WASM via tokio block_in_place
- [x] Guest memory read/write helpers (read_guest_bytes, write_guest_bytes)
- [x] 10s timeout, marge-plugin/1.0 user-agent
- Enables the entire Tier 3 cloud plugin ecosystem (Tuya, TP-Link, Spotify, etc.)
- **File**: `plugins.rs` (+224 LOC)

## Coverage Milestones
- **Current (Phases 1-6)**: ~70% of homes (MQTT Discovery + 4 bridges)
- **After 7.1-7.2 (Shelly + Hue)**: ~80% of homes
- **After 7.3-7.5 (Cast + Sonos + Matter)**: ~85% of homes
- **After 7.6 + cloud plugins**: ~90%+ of homes

## Working Pattern
- Each integration is a subagent task (Task tool) — keep main session as orchestrator
- Build + test after each integration
- Update this tracker after each commit
- CTS: 4818/4818 green as of 2026-02-16

---
## Session Log
- 2026-02-14: Phase 1 audit — all items verified implemented
- 2026-02-14: Phase 2/3 audit — all items verified implemented (were built during CTS depth batches)
- 2026-02-14: Fixed ws_connections missing from 5 test AppState constructors, 48/48 Rust tests pass
- 2026-02-14: Phase 4 round 1 — integrations REST API + responsive CSS (commit a601e89)
- 2026-02-14: Phase 4 round 2 — integrations UI tab + user accounts/argon2 (commit 6628011)
- 2026-02-14: Phase 4 round 3 — login page + visual automation editor (commit 46118cd)
- 2026-02-14: Phase 4 COMPLETE
- 2026-02-14: Phase 5+6 — backup restore + weather integration + WASM plugin runtime (commit 83ac375)
- 2026-02-16: CTS 4818/4818 green on clean restart, WS max_size fix (commit 6ca1087)
- 2026-02-16: Phase 7 roadmap written — local network integrations (Shelly, Hue, Cast, Sonos, Matter)
- 2026-02-16: Phase 7.1 Shelly integration (commit 518decd) — 470 LOC, Gen1+Gen2, 7 unit tests
- 2026-02-16: Phase 7.2 Philips Hue integration (commit cb18e20) — 676 LOC, pairing+polling, 7 unit tests
- 2026-02-16: Phase 7.6 WASM HTTP host functions (commit afb8785) — marge_http_get/post, +224 LOC
- 2026-02-16: 63/63 Rust unit tests green, React build clean
