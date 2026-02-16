# Marge WASM Plugin Examples

Example plugins demonstrating Marge's WebAssembly plugin system.

## Architecture Overview

Marge loads `.wasm` files from `/config/plugins/` at startup. Each plugin
runs in a sandboxed Wasmtime environment with fuel metering (1M fuel per
invocation) to prevent runaway execution. Plugins communicate with Marge
entirely through linear memory -- they write strings into their own memory
and pass `(pointer, length)` pairs to host functions.

## Plugin Lifecycle

1. **Load** -- Marge scans `/config/plugins/` for `*.wasm` files and
   compiles each one into a Wasmtime module.
2. **Init** -- If the plugin exports an `init()` function, Marge calls it
   once immediately after instantiation.
3. **Poll** -- If the plugin exports a `poll()` function, Marge calls it
   periodically (every 60 seconds by default).
4. **State change** -- If the plugin exports `on_state_changed()`, Marge
   calls it whenever an entity's state changes.

## Host Functions

Plugins import these functions from the `"env"` module:

| Function | Signature | Description |
|----------|-----------|-------------|
| `marge_log` | `(level: i32, msg_ptr: i32, msg_len: i32)` | Log a message. Levels: 0=error, 1=warn, 2=info, 3=debug |
| `marge_set_state` | `(entity_ptr: i32, entity_len: i32, state_ptr: i32, state_len: i32)` | Set an entity's state value |
| `marge_get_state` | `(entity_ptr: i32, entity_len: i32) -> i32` | Look up entity state (returns JSON length) |
| `marge_http_get` | `(url_ptr: i32, url_len: i32, buf_ptr: i32, buf_len: i32) -> i64` | HTTP GET; returns `(status << 32) \| body_len` |
| `marge_http_post` | `(url_ptr: i32, url_len: i32, body_ptr: i32, body_len: i32, buf_ptr: i32, buf_len: i32) -> i64` | HTTP POST; same return convention |

## Plugin Exports

| Export | Required | Description |
|--------|----------|-------------|
| `memory` | Yes | The plugin's linear memory (automatic for cdylib) |
| `init()` | No | Called once at load time |
| `poll()` | No | Called periodically (every 60s) |
| `on_state_changed(...)` | No | Called on entity state changes |

## Memory Model

WASM plugins run in their own isolated linear memory space. The calling
convention is:

- **Plugin to host** (e.g., setting state): The plugin writes the string
  data into its own memory, then calls the host function with a pointer
  and length. The host reads from the plugin's exported `memory`.

- **Host to plugin** (e.g., HTTP response): The plugin allocates a buffer
  in its own memory and passes `(buf_ptr, buf_len)` to the host. The host
  writes into that buffer and returns how many bytes it actually wrote.

Rust string literals (`&str`) live in the WASM data segment and can be
passed directly via `as_ptr()` / `len()`. For dynamic data, use a static
mutable buffer (WASM is single-threaded).

## Building a Plugin

Prerequisites:

```bash
rustup target add wasm32-unknown-unknown
```

Build:

```bash
cd examples/plugins/joke-sensor
cargo build --target wasm32-unknown-unknown --release
```

The compiled plugin will be at:

```
target/wasm32-unknown-unknown/release/joke_sensor.wasm
```

## Installing a Plugin

Copy the `.wasm` file into Marge's plugin directory:

```bash
cp target/wasm32-unknown-unknown/release/joke_sensor.wasm /config/plugins/
```

Or with Docker:

```bash
docker cp target/wasm32-unknown-unknown/release/joke_sensor.wasm marge:/config/plugins/
```

Restart Marge (or trigger a plugin reload) to load the new plugin.

## Example Plugins

### joke-sensor

Fetches random jokes from a public API and publishes them as
`sensor.joke`. Demonstrates:

- `init()` / `poll()` lifecycle
- `marge_set_state` for entity creation and updates
- `marge_http_get` for external API calls
- `marge_log` for structured logging
- Zero-dependency JSON parsing (no serde, ~2 KB .wasm)
- Static buffer allocation for HTTP responses

## Fuel Metering

Each plugin invocation (init, poll, on_state_changed) gets 1,000,000 fuel
units. This prevents infinite loops from blocking the server. If a plugin
exhausts its fuel, the call traps and Marge logs a warning. Normal plugins
use a tiny fraction of this budget.

## Debugging

Plugin log messages appear in Marge's tracing output with the plugin name:

```
INFO  marge::plugins: joke-sensor plugin initializing  plugin="joke_sensor"
INFO  marge::plugins: marge_set_state  plugin="joke_sensor" entity_id="sensor.joke" state="Loading..."
```

Set `RUST_LOG=marge::plugins=debug` to see all plugin activity including
HTTP requests and poll cycles.
