# Marge Plugin Examples

Marge supports two plugin runtimes: **WASM** (Rust/C compiled to WebAssembly) and
**Lua** (embedded Lua 5.4 via mlua). Both are loaded from `/config/plugins/` at
startup.

## Quick Start

Drop a `.lua` or `.wasm` file into `/config/plugins/` and restart Marge.

## Lua Plugins (Recommended)

Lua plugins are plain `.lua` files — no compilation step, no build toolchain.

### Plugin Contract

| Function | Required | Description |
|----------|----------|-------------|
| `init()` | No | Called once at load time |
| `poll()` | No | Called every 60 seconds |
| `on_state_changed(entity_id, old_state, new_state)` | No | Called on entity state changes |

### API Reference (`marge.*`)

| Function | Description |
|----------|-------------|
| `marge.log(level, msg)` | Log a message. Levels: `"error"`, `"warn"`, `"info"`, `"debug"` |
| `marge.get_state(entity_id)` | Returns `{state=, attributes={}}` or `nil` |
| `marge.set_state(entity_id, state, attrs?)` | Set entity state. `attrs` is an optional table |
| `marge.call_service(domain, service, data?)` | Call a service (e.g., `"light"`, `"turn_on"`) |
| `marge.http_get(url)` | HTTP GET. Returns `{status=, body=}` |
| `marge.http_post(url, body)` | HTTP POST. Returns `{status=, body=}` |

### Sandbox

Lua plugins run in a restricted environment:

- **Allowed**: `table`, `string`, `math`, `utf8`, `coroutine` standard libraries
- **Blocked**: `os`, `io`, `debug`, `package`, `loadfile`, `dofile`, `require`, `load`
- **Instruction limit**: 1M instructions per invocation (prevents infinite loops)

### Example: joke-sensor.lua

```lua
local ENTITY_ID = "sensor.joke"
local JOKE_URL  = "https://official-joke-api.appspot.com/random_joke"

function init()
    marge.log("info", "joke-sensor: initializing")
    marge.set_state(ENTITY_ID, "Loading...")
end

function poll()
    local resp = marge.http_get(JOKE_URL)
    if resp and resp.status == 200 then
        local setup = resp.body:match('"setup"%s*:%s*"(.-)"')
        local punchline = resp.body:match('"punchline"%s*:%s*"(.-)"')
        if setup and punchline then
            marge.set_state(ENTITY_ID, setup .. " -- " .. punchline)
        end
    end
end
```

### Example: motion-light.lua

```lua
local MOTION_SENSOR = "binary_sensor.motion"
local TARGET_LIGHT  = "light.hallway"

function on_state_changed(entity_id, old_state, new_state)
    if entity_id ~= MOTION_SENSOR then return end
    if new_state == "on" then
        marge.call_service("light", "turn_on", {
            entity_id = TARGET_LIGHT,
            brightness = 255,
        })
    elseif new_state == "off" then
        marge.call_service("light", "turn_off", {
            entity_id = TARGET_LIGHT,
        })
    end
end
```

## WASM Plugins

WASM plugins are compiled Rust (or C) binaries. They provide maximum performance
but require a build toolchain.

### Prerequisites

```bash
rustup target add wasm32-unknown-unknown
```

### Building

```bash
cd examples/plugins/joke-sensor
cargo build --target wasm32-unknown-unknown --release
cp target/wasm32-unknown-unknown/release/joke_sensor.wasm /config/plugins/
```

### Host Functions

WASM plugins import from the `"env"` module:

| Function | Signature | Description |
|----------|-----------|-------------|
| `marge_log` | `(level: i32, msg_ptr: i32, msg_len: i32)` | Log a message |
| `marge_set_state` | `(entity_ptr, entity_len, state_ptr, state_len)` | Set entity state |
| `marge_get_state` | `(entity_ptr, entity_len) -> i32` | Look up entity state |
| `marge_http_get` | `(url_ptr, url_len, buf_ptr, buf_len) -> i64` | HTTP GET |
| `marge_http_post` | `(url_ptr, url_len, body_ptr, body_len, buf_ptr, buf_len) -> i64` | HTTP POST |

### Memory Model

WASM plugins communicate through linear memory with `(pointer, length)` pairs.
See the `joke-sensor/` Rust example for the full pattern.

## Side-by-Side Comparison

| | Lua | WASM |
|---|---|---|
| **Lines of code** | ~35 (joke-sensor.lua) | ~353 (joke-sensor Rust) |
| **Build step** | None | `cargo build --target wasm32-unknown-unknown` |
| **Memory model** | Direct Lua tables | Manual pointer/length pairs |
| **Sandbox** | StdLib allowlist + instruction limit | Fuel metering (1M fuel/invocation) |
| **Performance** | Native (mlua FFI) | Near-native (Wasmtime JIT) |
| **Best for** | Automations, glue logic | Performance-critical, untrusted code |

## Fuel / Instruction Metering

Both runtimes limit execution to prevent runaway plugins:

- **WASM**: 1,000,000 fuel units per invocation (Wasmtime fuel metering)
- **Lua**: 1,000,000 instruction budget per invocation (hook-based counter)

If a plugin exceeds its budget, the call is aborted and Marge logs a warning.

## Debugging

Plugin log messages appear in Marge's tracing output:

```
INFO  marge::lua_plugins: joke-sensor.lua: updated sensor.joke  source="lua_plugin"
INFO  marge::plugins: marge_set_state  plugin="joke_sensor" entity_id="sensor.joke"
```

Set `RUST_LOG=marge=debug` to see all plugin activity.
