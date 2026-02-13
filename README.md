# MARGE

A clean-room reimplementation of Home Assistant's core automation engine in Rust. Built in 4 days for Innovation Week to answer: *what does a production home automation platform look like when built on proper foundations?*

Same YAML automations. Same MQTT entities. Same outcomes. Wildly different operational profile.

## The Numbers

| Metric | HA Stock | HA Slim | Marge | Ratio |
|---|---|---|---|---|
| Docker Image | 1.78 GB | 605 MB | 90 MB | 20x smaller |
| Memory (RSS) | 179 MB | 156 MB | 11 MB | 16x smaller |
| Cold Startup | ~94s | ~2.6s | 0.5 ms | 188,000x faster |
| Recovery Time | 20.4s | — | 5.7s | 3.6x faster |
| Avg Latency | 0.75 ms | 0.75 ms | 3.5 us | 214x faster |
| API Compat (CTS) | Baseline | Baseline | 77/77 | 100% |

HA Slim is a stripped-down HA image (core + frontend + MQTT only) to prove the gap is architectural, not packaging bloat.

## What's Here

```
marge-core/          Rust binary (axum + tokio + DashMap + rumqttd)
  src/api.rs           REST API (HA-compatible /api/states, /api/services, /api/health)
  src/websocket.rs     WebSocket event stream (subscribe_events, get_states)
  src/automation.rs    Trigger/condition/action engine (state, time, sun triggers)
  src/state.rs         Entity state machine (DashMap + broadcast channels)
  src/mqtt.rs          Embedded MQTT broker (rumqttd)
  src/scene.rs         Scene support (batch entity updates)

scenario-driver/     Python async driver — plays Day-in-the-Life scenario
dashboard/           Single-file HTML/CSS/JS — ASCII house + live metrics
tests/               77 pytest conformance tests (CTS)
ha-config/           Home Assistant configuration (MQTT entities, 6 automations)
docs/                Demo plan, Theory of Operations, System Spec, CTS spec
```

## Quick Start

```bash
docker compose up -d
# Dashboard: http://localhost:3000
# HA:        http://localhost:8123
# Marge:     http://localhost:8124

# Run the highlight reel (~10 min at demo speed)
docker compose run --rm -e SPEED=10 \
  -e CHAPTERS=dawn,morning,sunset,goodnight,outage \
  scenario-driver

# Press S in the dashboard for the score card
```

## The Demo

A simulated day in a house with 43 entities and 6 automations, run side-by-side against Home Assistant and Marge:

| Chapter | Sim Time | What Happens |
|---|---|---|
| **Dawn** | 05:30 | Morning automation: bedroom light, thermostat, coffee maker |
| **Morning** | 06:15 | Front door opens. Security condition evaluates (no false alert) |
| **Sunset** | 17:32 | Exterior lights + evening scene (7 state changes) |
| **Goodnight** | 22:00 | Bedside button: 12+ state changes, house goes dark |
| **Outage** | 03:47 | Power cut. Both killed. Recovery race. |

The dashboard shows an ASCII house visualization updating in real time, with side-by-side metrics (memory, latency, events, recovery timers).

## Architecture

```
┌──────────────────────────────────────────────────┐
│                 Docker Compose                    │
│                                                   │
│  mosquitto ──── ha-legacy ──── marge              │
│  (MQTT 1883)   (HA 8123)     (REST 8124)         │
│                               (MQTT 1884)         │
│                                                   │
│  scenario-driver ─── pushes same events to both   │
│  dashboard ───────── WebSocket to both (port 3000)│
└──────────────────────────────────────────────────┘
```

Marge implements:
- Embedded MQTT broker (rumqttd 0.19)
- HA-compatible REST API (GET/POST /api/states, POST /api/services)
- WebSocket event stream (subscribe_events protocol)
- Automation engine: state/time/sun triggers, state conditions, service call actions
- YAML parser for HA automations.yaml and scenes.yaml
- Sim-time management for accelerated scenarios

## Stats

- **1,550 lines of Rust** (marge-core)
- **835 lines of Python** (scenario driver)
- **1,120 lines of HTML/CSS/JS** (dashboard)
- **77 conformance tests** (pytest)
- **45 commits** in 9.5 hours (wall clock, one sitting)
- **100% AI-assisted** (Claude Code)

## Running the CTS

```bash
cd tests
pip install -r requirements.txt
pytest --tb=short -q
```

## License

This is an Innovation Week demo project. Use it however you want.
