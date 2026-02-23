# MARGE

A clean-room reimplementation of Home Assistant's core platform in Rust. Started as a 9.5-hour Innovation Week demo, now a working HA replacement covering ~85% of real-world homes.

Same YAML automations. Same MQTT entities. Same REST/WebSocket APIs. Same device bridges. Wildly different operational profile.

## The Numbers

| Metric | HA Stock | Marge | Ratio |
|---|---|---|---|
| Docker Image | 1.78 GB | 90 MB | 20x smaller |
| Memory (RSS) | 179 MB | 12 MB | 15x smaller |
| Cold Startup | ~94s | <1 ms | 188,000x faster |
| Avg Latency | 0.75 ms | 3.5 us | 214x faster |
| CTS Tests | Baseline | 4,843 passing | HA-compatible |
| Integrations | 2,800+ | 10 native + WASM plugins | Protocol-first |

## What's Here

```
marge-core/              Rust binary — 13,970 lines across 24 source files
  src/api.rs               REST API — HA-compatible + integrations + auth (2,518 LOC)
  src/automation.rs        Trigger/condition/action engine (1,220 LOC)
  src/services.rs          Dynamic service registry — 40 domains, 119 services (988 LOC)
  src/recorder.rs          SQLite persistence — WAL mode, write batching (873 LOC)
  src/discovery.rs         HA MQTT Discovery — 25 component types (832 LOC)
  src/plugins.rs           WASM plugin runtime — Wasmtime v29, fuel metering (595 LOC)
  src/websocket.rs         WebSocket event stream — 23 command types (554 LOC)
  src/template.rs          Jinja2 templates via minijinja (506 LOC)
  src/main.rs              Startup, wiring, signal handling (425 LOC)
  src/auth.rs              User accounts, argon2id hashing (236 LOC)
  src/mqtt.rs              Embedded MQTT broker — rumqttd 0.19 (229 LOC)
  src/state.rs             Entity state machine — DashMap + broadcast (169 LOC)
  src/scene.rs             Scene support (87 LOC)
  src/integrations/        10 device integrations (4,738 LOC total)
    shelly.rs                Shelly Gen1+Gen2 — HTTP polling, relay/light control (694 LOC)
    hue.rs                   Philips Hue — bridge pairing, light/sensor polling (676 LOC)
    matter.rs                Matter — python-matter-server sidecar manager (640 LOC)
    cast.rs                  Google Cast — eureka_info polling, media control (592 LOC)
    sonos.rs                 Sonos — UPnP discovery, zone management (580 LOC)
    zigbee2mqtt.rs           zigbee2mqtt bridge — MQTT topics, device registry (417 LOC)
    tasmota.rs               Tasmota bridge — telemetry parsing (344 LOC)
    zwave.rs                 zwave-js-ui bridge — command class mapping (302 LOC)
    esphome.rs               ESPHome bridge — component state mapping (270 LOC)
    weather.rs               Met.no weather — REST API poller (212 LOC)

marge-ui/               React 19 + TypeScript dashboard — 9,299 lines, 19 components
  8 tabs: Entities, Automations, Scenes, Areas, Devices/Labels, Integrations, Logs, Settings
  WebSocket real-time updates, auth gate, responsive layout

tests/                   CTS — 4,843 conformance tests across 415 pytest files
scenario-driver/         Python async driver — Day-in-the-Life demo scenario
dashboard/               ASCII house dashboard — Innovation Week demo UI
docs/                    Architecture, System Spec, Theory of Ops, Phase Tracker
```

## Quick Start

```bash
docker compose up -d
# Marge:     http://localhost:8124 (login: admin/admin)
# HA:        http://localhost:8123

# Run CTS
cd tests && pip install -r requirements.txt && pytest --tb=short -q
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full architecture document.

```
                         ┌──────────────────────────────────────┐
                         │          marge binary (:8124)        │
   HTTP/WS ────────────► │  axum router ─► state machine        │
                         │       │              │                │
                         │  service registry    broadcast        │
                         │       │              │                │
                         │  automation engine   recorder (SQLite)│
                         │       │              │                │
                         │  WASM plugin host    WebSocket push   │
                         │       │                               │
                         │  embedded MQTT broker (:1884)         │
                         └───────┼───────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────────┐
              ▼                  ▼                      ▼
        zigbee2mqtt        zwave-js-ui       Shelly / Hue / Cast
        (3,000+ Zigbee)    (2,000+ Z-Wave)   Sonos / Matter (local)
```

**Integration tiers:**
1. **MQTT bridges** — zigbee2mqtt, zwave-js-ui, Tasmota, ESPHome. Auto-discovered via HA MQTT Discovery protocol.
2. **HTTP polling** — Shelly (Gen1+Gen2), Philips Hue (bridge API), Google Cast, Sonos, Weather. Native Rust modules.
3. **Sidecar** — Matter (python-matter-server via WebSocket). Thread/BLE commissioning delegated to mature Python implementation.
4. **WASM plugins** — Cloud integrations (Tuya, Spotify, etc.). Sandboxed, fuel-metered, language-agnostic.

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | System architecture, module descriptions, data flow, WASM plugin system |
| [System Spec](docs/marge-sss.md) | MIL-STD-498 system specification |
| [Theory of Ops](docs/marge-theory-of-ops.md) | Operational concept, deployment, failure modes |
| [Phase Tracker](docs/phase-tracker.md) | Development roadmap and completion status |
| [CTS Spec](docs/marge-conformance-tests.md) | Conformance test suite design |
| [Pi SD Card Setup](docs/plan-pi-setup-sd.md) | Automated Pi SD card provisioning plan |

## Stats

- **13,970 lines of Rust** (marge-core)
- **9,299 lines of React/TypeScript** (marge-ui)
- **4,843 conformance tests** (CTS)
- **86 Rust unit tests**
- **272 commits**
- **10 native integrations**
- **100% AI-assisted** (Claude Code)

## License

MIT — see [LICENSE](LICENSE).
