# Marge Project Memory

## Project
- **Marge**: Clean-room HA reimplementation. Rust core + MQTT backbone.
- User: Director of Engineering, 25+ years embedded systems. Personal project for Innovation Week demo.
- Preferences: MIL-STD-498 style, depth over breadth, pushback = collaboration, markdown only, no emojis unless asked.
- The user wants autonomous execution — don't ask, just go.

## Architecture
- **Rust core**: axum 0.7 + tokio + DashMap + rumqttd 0.19 + rusqlite + minijinja + flate2/tar + argon2 + reqwest + wasmtime 29
- **React dashboard**: Vite + React 19 + TypeScript, served by Marge via tower-http ServeDir
- axum 0.7.x uses `:param` route syntax (NOT `{param}` — that's axum 0.8+)
- Automation engine: 6 YAML automations, RwLock-wrapped for hot-reload, metadata tracking
- Scene engine: 2 scenes (evening, goodnight)

## Key Files
- `marge-core/src/` — api.rs(~2100), auth.rs(~240), automation.rs(1220), discovery.rs(830), mqtt.rs(229), recorder.rs(~875), scene.rs(87), services.rs(851), state.rs(169), template.rs(506), websocket.rs(554), main.rs(~375), plugins.rs(~600)
- `marge-core/src/integrations/` — zigbee2mqtt.rs(417), zwave.rs(302), tasmota.rs(344), esphome.rs(269), weather.rs(212), shelly.rs(470), hue.rs(676), cast.rs, sonos.rs, matter.rs(460)
- `marge-ui/src/` — App.tsx(~960), IntegrationManager.tsx(~980), AutomationEditor.tsx(487), LoginPage.tsx(74), EntityCard.tsx(836), EntityDetail.tsx(815), + 12 more
- `tests/` — 4854+ CTS tests across 120+ test files

## Phase Tracker
See [phase-tracker.md](phase-tracker.md) for detailed status.
- **Phase 1 (Foundation)**: COMPLETE — SQLite, MQTT Discovery, minijinja, service registry
- **Phase 2 (Device Bridges)**: COMPLETE — zigbee2mqtt, zwave, tasmota, esphome
- **Phase 3 (Automation Engine)**: COMPLETE — time/sun triggers, scripts, templates
- **Phase 4 (Frontend + Auth)**: COMPLETE — 8-tab UI, login, automation editor, integrations
- **Phase 5 (Plugin System)**: MOSTLY COMPLETE — WASM runtime, weather, webhooks
- **Phase 6 (Production)**: MOSTLY COMPLETE — backup/restore, graceful shutdown, history
- **Phase 7 (Local Network)**: COMPLETE — Shelly, Hue, Cast, Sonos, Matter + WASM HTTP host functions
- **Coverage**: ~85% of homes (10 integrations)
- CTS: 1922 tests / 172 files (pruned from 4854/411 on 2026-02-16), 86/86 Rust unit tests

## Critical Gotchas
- **rumqttd 0.19**: No Default for ServerSettings, `broker.start()` is blocking (use spawn_blocking)
- **Entity count inflation**: CTS performance tests create 1000 test entities. Force-recreate for clean metrics
- **Cargo build**: Must run from `marge-core/` directory, not project root
- **Recorder coalesce**: 100ms write batching — tests need 150ms+ sleep between writes for history verification
- **conftest.py API**: `rest.base_url` (not `.base`), `ws.send_command(cmd, **kwargs)` (not positional dict)
- **Jinja2 precedence**: `{{ 10 / 3 | round(2) }}` applies round to 3 first; need parens `{{ (10 / 3) | round(2) }}`
- **Logbook dedup**: Logbook deduplicates consecutive identical state values (by design)
- **AppState test constructors**: Must include all fields (ws_connections, plugin_count) — 5 files have test constructors
