//! Lua Plugin Runtime (Phase 8 -- Lua scripting)
//!
//! Provides a sandboxed Lua 5.4 plugin execution environment using mlua.
//! Plugins are `.lua` files loaded from `/config/lua_plugins/`.
//!
//! Sandbox restrictions:
//! - Only TABLE, STRING, MATH, UTF8, COROUTINE standard libraries loaded
//! - No os, io, debug, package libraries
//! - Dangerous globals (loadfile, dofile, require, load) removed
//! - Instruction limit: 1M VM instructions per invocation (via set_hook)
//!
//! Host API available to plugins as `marge.*`:
//! - `marge.log(level, msg)` -- log via tracing
//! - `marge.get_state(entity_id)` -- returns {state=, attributes=} or nil
//! - `marge.set_state(entity_id, state, attributes?)` -- sets entity state
//! - `marge.call_service(domain, service, data?)` -- calls a service
//! - `marge.http_get(url)` -- HTTP GET, returns {status=, body=}
//! - `marge.http_post(url, body)` -- HTTP POST, returns {status=, body=}
//!
//! Plugins implement: `init()`, `on_state_changed(entity_id, old, new)`, `poll()`

use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use mlua::prelude::*;

use crate::api::AppState;
use crate::services::ServiceRegistry;

/// Maximum VM instructions per plugin invocation.
const INSTRUCTION_BUDGET: u64 = 1_000_000;

/// Hook fires every N instructions to check budget.
const HOOK_GRANULARITY: u32 = 10_000;

/// Convert mlua::Error to anyhow::Error.
///
/// mlua::Error contains `Arc<dyn StdError>` which is not Send+Sync,
/// so we can't use the `?` operator directly with anyhow. This helper
/// stringifies the error to produce an anyhow-compatible error.
fn lua_err(e: mlua::Error) -> anyhow::Error {
    anyhow::anyhow!("{}", e)
}

// ── Loaded plugin ───────────────────────────────────────────

/// A compiled and loaded Lua plugin.
struct LuaPlugin {
    name: String,
    lua: Lua,
    instruction_counter: Arc<AtomicU64>,
}

// ── Plugin Manager ──────────────────────────────────────────

/// Manages the lifecycle of all loaded Lua plugins.
pub struct LuaPluginManager {
    plugins: Vec<LuaPlugin>,
    app: Arc<AppState>,
    service_registry: Arc<std::sync::RwLock<ServiceRegistry>>,
    http_client: reqwest::Client,
    tokio_handle: tokio::runtime::Handle,
}

impl LuaPluginManager {
    /// Create a new Lua plugin manager.
    pub fn new(
        app: Arc<AppState>,
        service_registry: Arc<std::sync::RwLock<ServiceRegistry>>,
    ) -> Self {
        let http_client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .user_agent("marge-lua-plugin/1.0")
            .build()
            .expect("Failed to create HTTP client for Lua plugins");

        Self {
            plugins: Vec::new(),
            app,
            service_registry,
            http_client,
            tokio_handle: tokio::runtime::Handle::current(),
        }
    }

    /// Load a single `.lua` plugin from disk.
    pub fn load_plugin(&mut self, path: &Path) -> anyhow::Result<()> {
        let plugin_name = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string();

        tracing::info!(plugin = %plugin_name, path = %path.display(), "Loading Lua plugin");

        // Read source
        let source = std::fs::read_to_string(path)?;

        // Create sandboxed Lua with only safe standard libraries
        let lua = Lua::new_with(
            LuaStdLib::TABLE
                | LuaStdLib::STRING
                | LuaStdLib::MATH
                | LuaStdLib::UTF8
                | LuaStdLib::COROUTINE,
            LuaOptions::default(),
        )
        .map_err(lua_err)?;

        // Remove residual dangerous globals
        {
            let globals = lua.globals();
            for name in &["loadfile", "dofile", "require", "load"] {
                globals.set(*name, LuaValue::Nil).map_err(lua_err)?;
            }
        }

        // Set up instruction limit via hook
        let instruction_counter = Arc::new(AtomicU64::new(0));
        let counter_clone = instruction_counter.clone();
        lua.set_hook(
            mlua::HookTriggers::new().every_nth_instruction(HOOK_GRANULARITY),
            move |_lua, _debug| {
                let n = counter_clone.fetch_add(HOOK_GRANULARITY as u64, Ordering::Relaxed);
                if n + HOOK_GRANULARITY as u64 > INSTRUCTION_BUDGET {
                    Err(mlua::Error::RuntimeError(
                        "instruction limit exceeded (1M)".into(),
                    ))
                } else {
                    Ok(mlua::VmState::Continue)
                }
            },
        );

        // Register the marge.* API table
        register_api(
            &lua,
            &self.app,
            &self.service_registry,
            &self.http_client,
            &self.tokio_handle,
        )
        .map_err(lua_err)?;

        // Execute the plugin source code (defines functions)
        instruction_counter.store(0, Ordering::Relaxed);
        lua.load(&source)
            .set_name(&plugin_name)
            .exec()
            .map_err(lua_err)?;

        // Call init() if it exists
        let globals = lua.globals();
        if let Ok(func) = globals.get::<LuaFunction>("init") {
            instruction_counter.store(0, Ordering::Relaxed);
            func.call::<()>(()).map_err(lua_err)?;
            tracing::info!(plugin = %plugin_name, "Lua plugin init() completed");
        }

        self.plugins.push(LuaPlugin {
            name: plugin_name,
            lua,
            instruction_counter,
        });

        Ok(())
    }

    /// Scan a directory for `*.lua` files and load each one.
    pub fn scan_and_load(&mut self, dir: &Path) {
        let entries = match std::fs::read_dir(dir) {
            Ok(entries) => entries,
            Err(e) => {
                tracing::warn!(dir = %dir.display(), error = %e, "Failed to read Lua plugin directory");
                return;
            }
        };
        let mut count = 0;
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("lua") {
                match self.load_plugin(&path) {
                    Ok(()) => count += 1,
                    Err(e) => {
                        tracing::error!(path = %path.display(), error = %e, "Failed to load Lua plugin");
                    }
                }
            }
        }
        tracing::info!(dir = %dir.display(), count, "Lua plugin scan complete");
    }

    /// Notify all loaded plugins of a state change.
    ///
    /// Calls each plugin's `on_state_changed(entity_id, old_state, new_state)`
    /// if defined. Resets the instruction budget before each call.
    pub fn notify_state_change(&mut self, entity_id: &str, old_state: &str, new_state: &str) {
        for plugin in &mut self.plugins {
            let globals = plugin.lua.globals();
            if let Ok(func) = globals.get::<LuaFunction>("on_state_changed") {
                plugin.instruction_counter.store(0, Ordering::Relaxed);
                if let Err(e) = func.call::<()>((entity_id, old_state, new_state)) {
                    tracing::warn!(
                        plugin = %plugin.name,
                        entity_id,
                        error = %e,
                        "Lua on_state_changed error"
                    );
                }
            }
        }
    }

    /// Call `poll()` on all loaded plugins that define it.
    ///
    /// Resets the instruction budget before each call.
    pub fn poll_all(&mut self) {
        for plugin in &mut self.plugins {
            let globals = plugin.lua.globals();
            if let Ok(func) = globals.get::<LuaFunction>("poll") {
                plugin.instruction_counter.store(0, Ordering::Relaxed);
                if let Err(e) = func.call::<()>(()) {
                    tracing::warn!(
                        plugin = %plugin.name,
                        error = %e,
                        "Lua poll() error"
                    );
                }
            }
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

// ── Host API registration ───────────────────────────────────

/// Register the `marge.*` API table in the Lua environment.
///
/// Provides host functions for state management, service calls,
/// HTTP requests, and logging.
fn register_api(
    lua: &Lua,
    app: &Arc<AppState>,
    service_registry: &Arc<std::sync::RwLock<ServiceRegistry>>,
    http_client: &reqwest::Client,
    tokio_handle: &tokio::runtime::Handle,
) -> LuaResult<()> {
    let marge = lua.create_table()?;

    // ── marge.log(level, msg) ───────────────────────────────
    marge.set(
        "log",
        lua.create_function(|_, (level, msg): (String, String)| {
            match level.as_str() {
                "error" => tracing::error!(source = "lua_plugin", "{}", msg),
                "warn" | "warning" => tracing::warn!(source = "lua_plugin", "{}", msg),
                "info" => tracing::info!(source = "lua_plugin", "{}", msg),
                _ => tracing::debug!(source = "lua_plugin", "{}", msg),
            }
            Ok(())
        })?,
    )?;

    // ── marge.get_state(entity_id) -> {state=, attributes=} or nil
    let app_clone = app.clone();
    marge.set(
        "get_state",
        lua.create_function(move |lua, entity_id: String| {
            match app_clone.state_machine.get(&entity_id) {
                Some(entity_state) => {
                    let tbl = lua.create_table()?;
                    tbl.set("state", entity_state.state.clone())?;
                    let attrs = lua.create_table()?;
                    for (k, v) in &entity_state.attributes {
                        attrs.set(k.clone(), json_to_lua(lua, v)?)?;
                    }
                    tbl.set("attributes", attrs)?;
                    Ok(LuaValue::Table(tbl))
                }
                None => Ok(LuaValue::Nil),
            }
        })?,
    )?;

    // ── marge.set_state(entity_id, state, attributes_table?) ─
    let app_clone = app.clone();
    marge.set(
        "set_state",
        lua.create_function(
            move |_, (entity_id, state, attrs): (String, String, Option<LuaTable>)| {
                let attributes = match attrs {
                    Some(tbl) => lua_table_to_json_map(&tbl)?,
                    None => serde_json::Map::new(),
                };
                app_clone
                    .state_machine
                    .set(entity_id, state, attributes);
                Ok(())
            },
        )?,
    )?;

    // ── marge.call_service(domain, service, data_table?) ─────
    let app_clone = app.clone();
    let sr_clone = service_registry.clone();
    marge.set(
        "call_service",
        lua.create_function(
            move |_, (domain, service, data): (String, String, Option<LuaTable>)| {
                let data_value = match data {
                    Some(tbl) => {
                        let map = lua_table_to_json_map(&tbl)?;
                        serde_json::Value::Object(map)
                    }
                    None => serde_json::Value::Object(serde_json::Map::new()),
                };
                // Extract entity_id from data if present
                let entity_ids: Vec<String> =
                    if let Some(eid) = data_value.get("entity_id").and_then(|v| v.as_str()) {
                        vec![eid.to_string()]
                    } else {
                        Vec::new()
                    };
                if let Ok(registry) = sr_clone.read() {
                    registry.call(
                        &domain,
                        &service,
                        &entity_ids,
                        &data_value,
                        &app_clone.state_machine,
                    );
                }
                Ok(())
            },
        )?,
    )?;

    // ── marge.http_get(url) -> {status=, body=} ──────────────
    let client_clone = http_client.clone();
    let handle_clone = tokio_handle.clone();
    marge.set(
        "http_get",
        lua.create_function(move |lua, url: String| {
            let client = client_clone.clone();
            let handle = handle_clone.clone();
            let result = tokio::task::block_in_place(|| {
                handle.block_on(async { client.get(&url).send().await })
            });
            match result {
                Ok(resp) => {
                    let status = resp.status().as_u16();
                    let body = tokio::task::block_in_place(|| {
                        handle.block_on(async { resp.text().await })
                    })
                    .unwrap_or_default();
                    let tbl = lua.create_table()?;
                    tbl.set("status", status)?;
                    tbl.set("body", body)?;
                    Ok(LuaValue::Table(tbl))
                }
                Err(e) => {
                    let tbl = lua.create_table()?;
                    tbl.set("status", 0)?;
                    tbl.set("body", format!("Error: {}", e))?;
                    Ok(LuaValue::Table(tbl))
                }
            }
        })?,
    )?;

    // ── marge.http_post(url, body) -> {status=, body=} ───────
    let client_clone = http_client.clone();
    let handle_clone = tokio_handle.clone();
    marge.set(
        "http_post",
        lua.create_function(move |lua, (url, body): (String, String)| {
            let client = client_clone.clone();
            let handle = handle_clone.clone();
            let result = tokio::task::block_in_place(|| {
                handle.block_on(async {
                    client
                        .post(&url)
                        .header("Content-Type", "application/json")
                        .body(body)
                        .send()
                        .await
                })
            });
            match result {
                Ok(resp) => {
                    let status = resp.status().as_u16();
                    let body = tokio::task::block_in_place(|| {
                        handle.block_on(async { resp.text().await })
                    })
                    .unwrap_or_default();
                    let tbl = lua.create_table()?;
                    tbl.set("status", status)?;
                    tbl.set("body", body)?;
                    Ok(LuaValue::Table(tbl))
                }
                Err(e) => {
                    let tbl = lua.create_table()?;
                    tbl.set("status", 0)?;
                    tbl.set("body", format!("Error: {}", e))?;
                    Ok(LuaValue::Table(tbl))
                }
            }
        })?,
    )?;

    lua.globals().set("marge", marge)?;
    Ok(())
}

// ── JSON <-> Lua conversion helpers ─────────────────────────

/// Convert a serde_json::Value to a Lua value.
fn json_to_lua(lua: &Lua, value: &serde_json::Value) -> LuaResult<LuaValue> {
    match value {
        serde_json::Value::Null => Ok(LuaValue::Nil),
        serde_json::Value::Bool(b) => Ok(LuaValue::Boolean(*b)),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(LuaValue::Integer(i))
            } else if let Some(f) = n.as_f64() {
                Ok(LuaValue::Number(f))
            } else {
                Ok(LuaValue::Nil)
            }
        }
        serde_json::Value::String(s) => Ok(LuaValue::String(lua.create_string(s)?)),
        serde_json::Value::Array(arr) => {
            let tbl = lua.create_table()?;
            for (i, v) in arr.iter().enumerate() {
                tbl.set(i + 1, json_to_lua(lua, v)?)?;
            }
            Ok(LuaValue::Table(tbl))
        }
        serde_json::Value::Object(map) => {
            let tbl = lua.create_table()?;
            for (k, v) in map {
                tbl.set(k.clone(), json_to_lua(lua, v)?)?;
            }
            Ok(LuaValue::Table(tbl))
        }
    }
}

/// Convert a Lua value to a serde_json::Value.
#[allow(dead_code)]
fn lua_to_json(value: &LuaValue) -> LuaResult<serde_json::Value> {
    match value {
        LuaValue::Nil => Ok(serde_json::Value::Null),
        LuaValue::Boolean(b) => Ok(serde_json::Value::Bool(*b)),
        LuaValue::Integer(i) => Ok(serde_json::json!(*i)),
        LuaValue::Number(f) => Ok(serde_json::json!(*f)),
        LuaValue::String(s) => Ok(serde_json::Value::String(s.to_str()?.to_string())),
        LuaValue::Table(tbl) => {
            let map = lua_table_to_json_map(tbl)?;
            Ok(serde_json::Value::Object(map))
        }
        _ => Ok(serde_json::Value::Null),
    }
}

/// Convert a Lua table to a serde_json::Map.
fn lua_table_to_json_map(
    tbl: &LuaTable,
) -> LuaResult<serde_json::Map<String, serde_json::Value>> {
    let mut map = serde_json::Map::new();
    for pair in tbl.pairs::<LuaValue, LuaValue>() {
        let (k, v) = pair?;
        let key = match &k {
            LuaValue::String(s) => s.to_str()?.to_string(),
            LuaValue::Integer(i) => i.to_string(),
            _ => continue,
        };
        map.insert(key, lua_to_json(&v)?);
    }
    Ok(map)
}

// ── Tests ───────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn test_app_state() -> Arc<AppState> {
        Arc::new(AppState {
            state_machine: crate::state::StateMachine::new(16),
            started_at: std::time::Instant::now(),
            startup_us: std::sync::atomic::AtomicU64::new(0),
            sim_time: std::sync::Mutex::new(String::new()),
            sim_chapter: std::sync::Mutex::new(String::new()),
            sim_speed: std::sync::atomic::AtomicU32::new(0),
            ws_connections: std::sync::atomic::AtomicU32::new(0),
            plugin_count: std::sync::atomic::AtomicUsize::new(0),
        })
    }

    fn test_service_registry() -> Arc<std::sync::RwLock<ServiceRegistry>> {
        Arc::new(std::sync::RwLock::new(ServiceRegistry::new()))
    }

    fn test_manager() -> LuaPluginManager {
        LuaPluginManager::new(test_app_state(), test_service_registry())
    }

    #[tokio::test]
    async fn test_sandbox_no_os() {
        let mut mgr = test_manager();
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_os.lua");
        std::fs::write(&path, "function init() os.execute('ls') end").unwrap();
        let result = mgr.load_plugin(&path);
        assert!(result.is_err(), "os.execute should not be available in sandbox");
    }

    #[tokio::test]
    async fn test_sandbox_no_io() {
        let mut mgr = test_manager();
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_io.lua");
        std::fs::write(&path, "function init() io.open('foo') end").unwrap();
        let result = mgr.load_plugin(&path);
        assert!(result.is_err(), "io.open should not be available in sandbox");
    }

    #[tokio::test]
    async fn test_set_state() {
        let app = test_app_state();
        let sr = test_service_registry();
        let mut mgr = LuaPluginManager::new(app.clone(), sr);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_set.lua");
        std::fs::write(
            &path,
            r#"
            function init()
                marge.set_state("sensor.test", "hello")
            end
        "#,
        )
        .unwrap();
        mgr.load_plugin(&path).unwrap();
        let state = app.state_machine.get("sensor.test").unwrap();
        assert_eq!(state.state, "hello");
    }

    #[tokio::test]
    async fn test_get_state() {
        let app = test_app_state();
        app.state_machine.set(
            "sensor.test".to_string(),
            "world".to_string(),
            serde_json::Map::new(),
        );
        let sr = test_service_registry();
        let mut mgr = LuaPluginManager::new(app.clone(), sr);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_get.lua");
        std::fs::write(
            &path,
            r#"
            function init()
                local s = marge.get_state("sensor.test")
                if s then
                    result_state = s.state
                end
            end
        "#,
        )
        .unwrap();
        mgr.load_plugin(&path).unwrap();
        let result: String = mgr.plugins[0].lua.globals().get("result_state").unwrap();
        assert_eq!(result, "world");
    }

    #[tokio::test]
    async fn test_on_state_changed() {
        let app = test_app_state();
        let sr = test_service_registry();
        let mut mgr = LuaPluginManager::new(app.clone(), sr);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_cb.lua");
        std::fs::write(
            &path,
            r#"
            changed_entity = ""
            function on_state_changed(entity_id, old_state, new_state)
                changed_entity = entity_id
            end
        "#,
        )
        .unwrap();
        mgr.load_plugin(&path).unwrap();
        mgr.notify_state_change("light.kitchen", "off", "on");
        let result: String = mgr.plugins[0]
            .lua
            .globals()
            .get("changed_entity")
            .unwrap();
        assert_eq!(result, "light.kitchen");
    }

    #[tokio::test]
    async fn test_poll_counter() {
        let app = test_app_state();
        let sr = test_service_registry();
        let mut mgr = LuaPluginManager::new(app, sr);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_poll.lua");
        std::fs::write(
            &path,
            r#"
            counter = 0
            function poll()
                counter = counter + 1
            end
        "#,
        )
        .unwrap();
        mgr.load_plugin(&path).unwrap();
        mgr.poll_all();
        mgr.poll_all();
        let count: i64 = mgr.plugins[0].lua.globals().get("counter").unwrap();
        assert_eq!(count, 2);
    }

    #[tokio::test]
    async fn test_instruction_limit() {
        let app = test_app_state();
        let sr = test_service_registry();
        let mut mgr = LuaPluginManager::new(app, sr);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test_inf.lua");
        std::fs::write(
            &path,
            r#"
            function poll()
                while true do end
            end
        "#,
        )
        .unwrap();
        mgr.load_plugin(&path).unwrap();
        // poll() should not hang -- the instruction limit should abort it
        mgr.poll_all();
        // If we get here, the limit worked
    }

    #[tokio::test]
    async fn test_json_roundtrip() {
        let lua = Lua::new();
        let original = serde_json::json!({
            "name": "test",
            "count": 42,
            "nested": {"a": true, "b": [1, 2, 3]},
            "pi": 3.14
        });
        let lua_val = json_to_lua(&lua, &original).unwrap();
        let roundtripped = lua_to_json(&lua_val).unwrap();
        assert_eq!(original["name"], roundtripped["name"]);
        assert_eq!(original["count"], roundtripped["count"]);
        assert_eq!(original["nested"]["a"], roundtripped["nested"]["a"]);
        assert_eq!(original["pi"], roundtripped["pi"]);
    }
}
