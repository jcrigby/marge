//! WASM Plugin Runtime (Phase 5 S5.1)
//!
//! Provides a sandboxed plugin execution environment using Wasmtime.
//! Plugins are `.wasm` files loaded from `/config/plugins/`.
//!
//! Host functions available to plugins:
//! - `marge_log(level, msg_ptr, msg_len)` -- logs via tracing at the requested level
//! - `marge_get_state(entity_ptr, entity_len) -> i32` -- returns JSON length written to memory
//! - `marge_set_state(entity_ptr, entity_len, state_ptr, state_len)` -- sets entity state
//!
//! Plugins implement: `fn init()`, `fn on_state_changed(entity_ptr, entity_len, old_ptr, old_len, new_ptr, new_len)`

use std::path::Path;
use std::sync::Arc;

use anyhow::{bail, Context, Result};
use wasmtime::{Caller, Engine, Extern, Instance, Linker, Module, Store};

use crate::api::AppState;

/// Fuel budget per plugin invocation -- prevents infinite loops.
const FUEL_PER_INVOCATION: u64 = 1_000_000;

// ── Per-plugin host-side state ──────────────────────────────

/// State accessible from within host functions via `Caller::data()`.
struct PluginState {
    app: Arc<AppState>,
    name: String,
}

// ── Loaded plugin ───────────────────────────────────────────

/// A compiled and instantiated WASM plugin.
#[allow(dead_code)]
struct LoadedPlugin {
    name: String,
    instance: Instance,
    store: Store<PluginState>,
}

// ── Plugin Manager ──────────────────────────────────────────

/// Manages the lifecycle of all loaded WASM plugins.
pub struct PluginManager {
    engine: Engine,
    plugins: Vec<LoadedPlugin>,
    app: Arc<AppState>,
}

impl PluginManager {
    /// Create a new plugin manager with fuel metering enabled.
    pub fn new(app: Arc<AppState>) -> Self {
        let mut config = wasmtime::Config::new();
        config.consume_fuel(true);

        let engine = Engine::new(&config).expect("Failed to create wasmtime engine");

        Self {
            engine,
            plugins: Vec::new(),
            app,
        }
    }

    /// Load a single `.wasm` plugin from disk.
    pub fn load_plugin(&mut self, path: &Path) -> Result<()> {
        let plugin_name = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string();

        tracing::info!(plugin = %plugin_name, path = %path.display(), "Loading WASM plugin");

        // Compile the module
        let wasm_bytes = std::fs::read(path)
            .with_context(|| format!("Failed to read plugin file: {}", path.display()))?;
        let module = Module::new(&self.engine, &wasm_bytes)
            .with_context(|| format!("Failed to compile plugin: {}", plugin_name))?;

        // Create per-plugin store with host state
        let plugin_state = PluginState {
            app: self.app.clone(),
            name: plugin_name.clone(),
        };
        let mut store = Store::new(&self.engine, plugin_state);

        // Provision initial fuel
        store
            .set_fuel(FUEL_PER_INVOCATION)
            .context("Failed to set initial fuel")?;

        // Build the linker and register host functions
        let mut linker: Linker<PluginState> = Linker::new(&self.engine);
        register_host_functions(&mut linker)?;

        // Instantiate the module
        let instance = linker
            .instantiate(&mut store, &module)
            .with_context(|| format!("Failed to instantiate plugin: {}", plugin_name))?;

        // Call `init` export if it exists
        if let Some(init_fn) = instance.get_typed_func::<(), ()>(&mut store, "init").ok() {
            store.set_fuel(FUEL_PER_INVOCATION)?;
            match init_fn.call(&mut store, ()) {
                Ok(()) => {
                    tracing::info!(plugin = %plugin_name, "Plugin init() completed");
                }
                Err(e) => {
                    tracing::warn!(plugin = %plugin_name, error = %e, "Plugin init() trapped");
                }
            }
        }

        self.plugins.push(LoadedPlugin {
            name: plugin_name,
            instance,
            store,
        });

        Ok(())
    }

    /// Scan a directory for `*.wasm` files and load each one.
    pub fn scan_and_load(&mut self, dir: &Path) {
        let entries = match std::fs::read_dir(dir) {
            Ok(entries) => entries,
            Err(e) => {
                tracing::warn!(dir = %dir.display(), error = %e, "Failed to read plugin directory");
                return;
            }
        };

        let mut count = 0;
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("wasm") {
                match self.load_plugin(&path) {
                    Ok(()) => count += 1,
                    Err(e) => {
                        tracing::error!(
                            path = %path.display(),
                            error = %e,
                            "Failed to load plugin"
                        );
                    }
                }
            }
        }

        tracing::info!(dir = %dir.display(), count, "Plugin scan complete");
    }

    /// Notify all loaded plugins of a state change.
    ///
    /// Calls each plugin's `on_state_changed` export if it exists.
    /// Uses fuel metering to prevent runaway execution and catches
    /// traps so one misbehaving plugin cannot crash the server.
    #[allow(dead_code)]
    pub fn notify_state_change(&mut self, entity_id: &str, old_state: &str, new_state: &str) {
        for plugin in &mut self.plugins {
            // Look up the exported callback.  The WASM-side signature is:
            //   fn on_state_changed(entity_ptr: i32, entity_len: i32,
            //                       old_ptr: i32,    old_len: i32,
            //                       new_ptr: i32,    new_len: i32)
            //
            // For the skeleton we use a simpler () -> () signature check first,
            // then fall back to the full signature.  Full memory-passing will be
            // implemented once a reference plugin is available.
            let callback = plugin
                .instance
                .get_typed_func::<(), ()>(&mut plugin.store, "on_state_changed");

            if let Ok(func) = callback {
                // Replenish fuel
                if let Err(e) = plugin.store.set_fuel(FUEL_PER_INVOCATION) {
                    tracing::warn!(
                        plugin = %plugin.name,
                        error = %e,
                        "Failed to set fuel for on_state_changed"
                    );
                    continue;
                }

                match func.call(&mut plugin.store, ()) {
                    Ok(()) => {
                        tracing::debug!(
                            plugin = %plugin.name,
                            entity_id,
                            "on_state_changed dispatched"
                        );
                    }
                    Err(e) => {
                        tracing::warn!(
                            plugin = %plugin.name,
                            entity_id,
                            error = %e,
                            "on_state_changed trapped"
                        );
                    }
                }
            }

            // Suppress unused-variable warnings for the string args until
            // full memory passing is wired up.
            let _ = (old_state, new_state);
        }
    }

    /// Number of successfully loaded plugins.
    pub fn plugin_count(&self) -> usize {
        self.plugins.len()
    }

    /// Return the names of all loaded plugins (for health/status endpoints).
    #[allow(dead_code)]
    pub fn plugin_names(&self) -> Vec<String> {
        self.plugins.iter().map(|p| p.name.clone()).collect()
    }
}

// ── Host function registration ──────────────────────────────

/// Register the `env` module host functions that plugins may import.
fn register_host_functions(linker: &mut Linker<PluginState>) -> Result<()> {
    // ── marge_log(level: i32, msg_ptr: i32, msg_len: i32) ───
    linker.func_wrap(
        "env",
        "marge_log",
        |mut caller: Caller<'_, PluginState>, level: i32, msg_ptr: i32, msg_len: i32| {
            let plugin_name = caller.data().name.clone();
            let msg = read_guest_string(&mut caller, msg_ptr, msg_len)
                .unwrap_or_else(|_| "<invalid utf-8>".to_string());

            match level {
                0 => tracing::error!(plugin = %plugin_name, "{}", msg),
                1 => tracing::warn!(plugin = %plugin_name, "{}", msg),
                2 => tracing::info!(plugin = %plugin_name, "{}", msg),
                _ => tracing::debug!(plugin = %plugin_name, "{}", msg),
            }
        },
    )?;

    // ── marge_get_state(entity_ptr: i32, entity_len: i32) -> i32 ──
    //
    // Looks up the entity state and returns a JSON string length.
    // TODO: Full implementation requires writing the JSON back into
    //       plugin linear memory via a shared-buffer protocol.
    //       For now, logs the lookup and returns 0.
    linker.func_wrap(
        "env",
        "marge_get_state",
        |mut caller: Caller<'_, PluginState>, entity_ptr: i32, entity_len: i32| -> i32 {
            let plugin_name = caller.data().name.clone();
            let entity_id = match read_guest_string(&mut caller, entity_ptr, entity_len) {
                Ok(s) => s,
                Err(e) => {
                    tracing::warn!(
                        plugin = %plugin_name,
                        error = %e,
                        "marge_get_state: failed to read entity_id"
                    );
                    return -1;
                }
            };

            let app = caller.data().app.clone();
            match app.state_machine.get(&entity_id) {
                Some(state) => {
                    tracing::debug!(
                        plugin = %plugin_name,
                        entity_id = %entity_id,
                        state = %state.state,
                        "marge_get_state: found"
                    );
                    // TODO: Write JSON into plugin memory and return length
                    0
                }
                None => {
                    tracing::debug!(
                        plugin = %plugin_name,
                        entity_id = %entity_id,
                        "marge_get_state: not found"
                    );
                    -1
                }
            }
        },
    )?;

    // ── marge_set_state(entity_ptr, entity_len, state_ptr, state_len) ──
    //
    // Sets an entity's state value. Attributes are not yet supported
    // in this skeleton; the full protocol will accept a JSON attributes
    // blob via an additional pointer/length pair.
    linker.func_wrap(
        "env",
        "marge_set_state",
        |mut caller: Caller<'_, PluginState>,
         entity_ptr: i32,
         entity_len: i32,
         state_ptr: i32,
         state_len: i32| {
            let plugin_name = caller.data().name.clone();

            let entity_id = match read_guest_string(&mut caller, entity_ptr, entity_len) {
                Ok(s) => s,
                Err(e) => {
                    tracing::warn!(
                        plugin = %plugin_name,
                        error = %e,
                        "marge_set_state: failed to read entity_id"
                    );
                    return;
                }
            };

            let state_val = match read_guest_string(&mut caller, state_ptr, state_len) {
                Ok(s) => s,
                Err(e) => {
                    tracing::warn!(
                        plugin = %plugin_name,
                        error = %e,
                        "marge_set_state: failed to read state value"
                    );
                    return;
                }
            };

            tracing::info!(
                plugin = %plugin_name,
                entity_id = %entity_id,
                state = %state_val,
                "marge_set_state"
            );

            let app = caller.data().app.clone();
            app.state_machine.set(
                entity_id,
                state_val,
                serde_json::Map::new(),
            );
        },
    )?;

    Ok(())
}

// ── Memory helpers ──────────────────────────────────────────

/// Read a UTF-8 string from the guest's linear memory at the given
/// pointer and length.
fn read_guest_string(
    caller: &mut Caller<'_, PluginState>,
    ptr: i32,
    len: i32,
) -> Result<String> {
    let mem = match caller.get_export("memory") {
        Some(Extern::Memory(mem)) => mem,
        _ => bail!("Plugin does not export 'memory'"),
    };

    let data = mem
        .data(&caller)
        .get(ptr as u32 as usize..)
        .and_then(|slice| slice.get(..len as u32 as usize))
        .ok_or_else(|| anyhow::anyhow!("Pointer/length out of bounds"))?;

    let s = std::str::from_utf8(data)
        .context("Invalid UTF-8 in guest memory")?;

    Ok(s.to_string())
}
