# CLAUDE.md — Project context for Claude Code

## What This Is
Marge: clean-room reimplementation of Home Assistant's core automation engine in Rust. Innovation Week demo. Built in one sitting (9.5 hours, 47 commits).

## Architecture
- **marge-core/**: Rust binary — axum 0.7 + tokio + DashMap + rumqttd 0.19
- **scenario-driver/**: Python async — plays Day-in-the-Life scenario against HA and Marge
- **dashboard/**: Single-file HTML/CSS/JS — ASCII house + live metrics + score card
- **tests/**: 77 pytest conformance tests (CTS)
- **ha-config/**: Home Assistant MQTT entity config + 6 automations + 2 scenes

## Docker Stack
```
mosquitto (1883) — ha-legacy (8123) — marge (8124/1884) — dashboard (3000)
```
- `docker compose up -d` starts the 4 main containers
- ha-slim (8125) is under the `slim` profile — `docker compose --profile slim up ha-slim`
- Scenario driver: `docker compose run --rm -e SPEED=10 -e CHAPTERS=dawn,morning,sunset,goodnight,outage scenario-driver`

## Key Gotchas
- axum **0.7.x** uses `:param` route syntax (NOT `{param}` — that's 0.8+)
- rumqttd 0.19: `broker.start()` is blocking — must use `spawn_blocking`
- Rust edition 2024, requires rustc 1.88+. Dockerfile uses `rust:1.93`
- HA tokens expire ~30 min. Refresh: `scripts/ha-refresh-token.sh`
- HA generates automation entity_ids from `alias` not `id` field
- HA MQTT entities expect uppercase ON/OFF payloads for binary sensors/lights/switches
- Cargo build must run from `marge-core/` directory, not project root
- Driver uses ENV vars (SPEED, CHAPTER, CHAPTERS, TARGET), not CLI args

## Working Preferences
- Autonomous execution preferred — don't ask, just go
- For multi-step implementation work, delegate each discrete task to a subagent (Task tool) rather than doing it inline. Keep the main session as the orchestrator.
- After each subagent completes, verify the work (build, tests), update memory breadcrumbs, then move to the next task.
- MIL-STD-498 style documentation in docs/
- No emojis unless asked
