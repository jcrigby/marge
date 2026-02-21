# Marge Project Memory

## Project
- **Marge**: Clean-room HA reimplementation. Rust core + MQTT backbone.
- User: Director of Engineering, 25+ years embedded systems. Personal project for Innovation Week demo.
- Preferences: MIL-STD-498 style, depth over breadth, pushback = collaboration, markdown only, no emojis unless asked.
- The user wants autonomous execution — don't ask, just go.

## Architecture
- **Rust core**: axum 0.7 + tokio + DashMap + rumqttd 0.19 + rusqlite + minijinja + flate2/tar + argon2 + reqwest + wasmtime 29 + mlua 0.10 (Lua 5.4)
- **React dashboard**: Vite + React 19 + TypeScript, served by Marge via tower-http ServeDir
- axum 0.7.x uses `:param` route syntax (NOT `{param}` — that's axum 0.8+)
- Automation engine: 6 YAML automations, RwLock-wrapped for hot-reload, metadata tracking
- Scene engine: 2 scenes (evening, goodnight)

## Key Files
- `marge-core/src/` — api.rs(~2100), auth.rs(~240), automation.rs(1220), discovery.rs(830), mqtt.rs(229), recorder.rs(~875), scene.rs(87), services.rs(851), state.rs(169), template.rs(506), websocket.rs(554), main.rs(~400), plugins.rs(~630), lua_plugins.rs(680), plugin_orchestrator.rs(116)
- `marge-core/src/integrations/` — zigbee2mqtt.rs(417), zwave.rs(302), tasmota.rs(344), esphome.rs(269), weather.rs(212), shelly.rs(470), hue.rs(676), cast.rs, sonos.rs, matter.rs(460)
- `marge-ui/src/` — App.tsx(~960), IntegrationManager.tsx(~980), AutomationEditor.tsx(487), LoginPage.tsx(74), EntityCard.tsx(836), EntityDetail.tsx(815), + 12 more
- `tests/` — 1654 CTS tests across 125 test files (pruned from 4854/411)
- `examples/plugins/` — joke-sensor/ (WASM, 353 LOC Rust), joke-sensor.lua (35 LOC), motion-light.lua (26 LOC)
- `virtual-devices/zigbee2mqtt/` — devices.py(485), simulator.py(500) — 37 device z2m simulator (paho-mqtt v2)
- `virtual-devices/shelly/` — simulator.py(225) — 2 Gen2 Shelly devices (FastAPI, port 8180)
- `virtual-devices/hue/` — simulator.py(280) — Hue bridge with 3 lights + 2 sensors (FastAPI, port 8181)

## Phase Tracker
See [phase-tracker.md](phase-tracker.md) for detailed status.
- **Phase 1 (Foundation)**: COMPLETE — SQLite, MQTT Discovery, minijinja, service registry
- **Phase 2 (Device Bridges)**: COMPLETE — zigbee2mqtt, zwave, tasmota, esphome
- **Phase 3 (Automation Engine)**: COMPLETE — time/sun triggers, scripts, templates
- **Phase 4 (Frontend + Auth)**: COMPLETE — 8-tab UI, login, automation editor, integrations
- **Phase 5 (Plugin System)**: COMPLETE — WASM + Lua runtimes, unified orchestrator, weather, webhooks
- **Phase 6 (Production)**: MOSTLY COMPLETE — backup/restore, graceful shutdown, history
- **Phase 7 (Local Network)**: COMPLETE — Shelly, Hue, Cast, Sonos, Matter + WASM HTTP host functions
- **Phase 8 (Virtual Devices)**: COMPLETE — zigbee2mqtt (37 devices), Shelly (2 Gen2), Hue (3 lights + 2 sensors) simulators
- **Phase 9 (Conformance Verification)**: COMPLETE — divergence matrix, A/B diff, conformance monitor, service response fix, marge_only markers, conformance gate
- **Coverage**: ~85% of homes (10 integrations)
- CTS: 1654 tests / 125 files (pruned from 4854/411 on 2026-02-16), 19 files tagged marge_only, 94/94 Rust unit tests
- Scripts: cts-compare.py (170 LOC), cts-dual-run.sh (120 LOC), ab-diff.py (249 LOC), conformance-monitor.py (300 LOC)

## Critical Gotchas
- **MQTT command dispatch**: `set_mqtt_tx()` must be called after `start_mqtt()` to wire service→broker publish. Uses a second broker link (`marge-command`) and `spawn_blocking` + `blocking_recv()` for the publisher task. Without this, service calls silently drop outbound MQTT commands
- **rumqttd 0.19**: No Default for ServerSettings, `broker.start()` is blocking (use spawn_blocking)
- **Entity count inflation**: CTS performance tests create 1000 test entities. Force-recreate for clean metrics
- **Cargo build**: Must run from `marge-core/` directory, not project root
- **Recorder coalesce**: 100ms write batching — tests need 150ms+ sleep between writes for history verification
- **conftest.py API**: `rest.base_url` (not `.base`), `ws.send_command(cmd, **kwargs)` (not positional dict)
- **Jinja2 precedence**: `{{ 10 / 3 | round(2) }}` applies round to 3 first; need parens `{{ (10 / 3) | round(2) }}`
- **Logbook dedup**: Logbook deduplicates consecutive identical state values (by design)
- **AppState test constructors**: Must include all fields (ws_connections, plugin_count) — 5 files have test constructors
- **mlua "send" feature**: Required for `Lua` to be `Send` (uses `Arc<ReentrantMutex>` internally). Without it, `Lua` uses `Rc` and can't cross `.await` points
- **mlua::Error -> anyhow**: `mlua::Error` contains `Arc<dyn StdError>` which isn't `Send+Sync`; must convert via `.map_err(|e| anyhow::anyhow!("{}", e))` — not `?` directly
- **State casing**: MQTT devices (zigbee2mqtt) use uppercase ON/OFF/LOCKED/ARMED_HOME. Discovery's `normalize_state()` converts to HA lowercase. Must apply AFTER template rendering AND JSON extraction, not just in `extract_state_from_payload`
- **Alarm MQTT service names**: Service names are "arm_night" not "alarm_arm_night" — match on both for safety
- **Docker restart vs recreate**: `docker compose restart` reuses same container image. Need `docker compose up -d --force-recreate` to pick up rebuilt images
- **HA token expiry**: Default tokens expire ~30 min. Run `./scripts/ha-refresh-token.sh` before each demo session. For walkaway resilience, create a long-lived token via HA UI (Profile > Long-Lived Access Tokens)

## Plan Decisions
<!-- Record architectural choices and WHY they were made. Prevents re-litigating settled decisions. -->
- **Phase 9 — Conformance Verification**: Rather than just running CTS and hoping, systematically compare HA vs Marge. Four deliverables: (1) CTS divergence matrix, (2) A/B structural diff, (3) conformance monitor, (4) fix known divergences. Chose pytest-json-report for machine-readable CTS output. Chose `marge_only` marker to filter Marge-specific tests when running against HA (rather than separate test dirs). Known divergence: service call response wraps in `{"changed_states": [...]}` vs HA's flat array.
- **Dual plugin runtime (WASM + Lua)**: WASM for performance-critical/compiled plugins, Lua for quick scripting. Both sandboxed. Chose this over Lua-only because WASM allows any source language.
- **Embedded MQTT broker (rumqttd)**: Avoids external dependency for demo. Trade-off: rumqttd 0.19 API is awkward (blocking start, no Default for ServerSettings).
- **SQLite over Postgres**: Single-binary deployment, no external DB. WAL mode for concurrent reads. Sufficient for home automation scale.
- **React UI served by Rust**: tower-http ServeDir serves built React assets. No separate web server needed.
- **Local network integrations as Rust modules, not plugins**: Shelly/Hue/Cast/Sonos/Matter need persistent connections, mDNS, event streams — too complex for WASM/Lua sandbox.

## Failed Approaches
<!-- What was tried and didn't work. Prevents repeating mistakes. -->
- **mlua without "send" feature**: `Lua` uses `Rc` internally, can't cross `.await` points. Wasted time debugging before discovering the feature flag.
- **Direct `?` with mlua::Error + anyhow**: `Arc<dyn StdError>` isn't `Send+Sync`. Must use `.map_err(|e| anyhow::anyhow!("{}", e))`.
- **CTS depth test explosion**: Auto-generated depth tests grew to 4854 tests / 411 files with massive duplication. Had to prune back to 1654/125. Lesson: generate focused tests, not combinatorial.
- **Docker `restart` vs `recreate`**: `docker compose restart` reuses the same image. Spent time debugging why code changes weren't taking effect. Need `up -d --force-recreate`.

## Discovered Blockers / Surprises
<!-- Things found during implementation that were unexpected and affect future work. -->
- **HA automation entity_ids from `alias` not `id`**: HA ignores the `id` field and generates entity_id from the `alias`. Caused entity mismatch confusion.
- **MQTT command dispatch requires second broker link**: Service calls need to publish back to MQTT. Required a separate `marge-command` client connection + `spawn_blocking` + `blocking_recv()`. Without this, outbound MQTT commands silently drop.
- **State casing normalization timing**: Must normalize AFTER template rendering AND JSON extraction. Normalizing too early breaks template logic.
- **HA service dispatch requires integration-registered entities**: `POST /api/states` creates state entries but does NOT register entities with HA's service platform. Calling `POST /api/services/light/turn_on` on an entity created via states API returns 400 on HA. Marge is lenient and dispatches to any entity in the state machine. This means 555 CTS tests (61% of failures) use an approach that's fundamentally incompatible with HA. Tests must either use HA-native entities or only assert via state API.

## Known Issues (Resolved)
- **ServiceResponse format divergence**: Marge wrapped service call responses in `{"changed_states": [...]}` while HA returns a flat `[...]`. Fixed in Phase 9.3 — handler now returns `Json<Vec<EntityState>>` directly. 4 test files updated.

## Known Conformance Gaps (from Phase 9.7 dual CTS run)
CTS conformance: 580/1490 (38.9%). 909 tests pass on Marge but fail on HA.

**Bucket C — Real bugs in Marge (69 tests, 7 issues):**
1. **WS get_services format** (13 tests): Marge returns `[{domain, services}]`, HA returns `{domain: {service: {...}}}`. Fix: `websocket.rs`
2. **Service domain listing** (23 tests): Marge lists 40+ domains statically; HA only lists domains with loaded integrations. Decision needed: lazy-load or tag marge_only.
3. **Template WS render_template** (14 tests): Different result wrapping. Fix: match HA's WS response format.
4. **Template filter differences** (7 tests): `int(3.14)` → 0 on HA, 3 on Marge. `is_defined` returns value vs true. None vs none casing. Fix: `template.rs`
5. **Context ID format** (2 tests): HA=ULIDs (26 chars, no dashes), Marge=UUIDs. Fix: generate ULIDs.
6. **POST /api/states 201 vs 200** (2 tests): HA returns 201 Created for new entities. Fix: `api.rs` state setter.
7. **Misc** (3 tests): HA returns 500 for missing template field, WS error format, subscribe_trigger.

**Bucket B — Test approach problem (555 tests):**
Root cause: tests create entities via `POST /api/states` then call services on them. HA's service dispatcher requires entities to be registered through integrations — `POST /api/states` only sets state, doesn't register with the platform. Marge is lenient and accepts any entity. These tests need rewriting to use HA-compatible patterns (either HA entities or state-only assertions).

**Bucket A — Marge-only endpoints (285 tests):**
Need `marge_only` marker: history REST, logbook REST, areas/labels/devices REST, config YAML endpoints, notifications, backup, webhooks, statistics, recorder.

**Full categorization:** `cts-results/manual-run/categorization.json`

## Known Issues (Not Yet Fixed)
- **Memory leak — topic_subscriptions**: `discovery.rs:462` `add_topic_subscription()` pushes entity_ids into `Vec<String>` without dedup. Each MQTT message re-appends the same IDs. Over 3 days with 37 devices @ 5s intervals = millions of duplicate strings (~50-100 MB). **Fix**: Change `Vec<String>` to `HashSet<String>` or add dedup check before push.
- **Memory leak — last_time_triggers**: `automation.rs:661` stores `"automation_id:HH:MM"` keys to prevent duplicate time-trigger fires, but only clears on automation reload. Grows ~10-20 MB over days. **Fix**: Add TTL cleanup (remove entries older than 24h) or clear daily.
- **Possible — SQLite WAL growth**: `recorder.rs` uses WAL mode. Over days of continuous writes, WAL segments could accumulate if checkpoint lags. Monitor `.db-wal` file size.
