//! Plugin Orchestrator (Phase 8)
//!
//! Wraps both WasmPluginManager and LuaPluginManager behind a single
//! interface. Spawns background tasks for periodic polling and
//! state-change dispatch.

use std::path::Path;
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::api::AppState;
use crate::lua_plugins::LuaPluginManager;
use crate::plugins::PluginManager as WasmPluginManager;
use crate::services::ServiceRegistry;

/// Unified plugin orchestrator wrapping both WASM and Lua runtimes.
pub struct PluginOrchestrator {
    wasm: WasmPluginManager,
    lua: LuaPluginManager,
}

impl PluginOrchestrator {
    /// Create a new orchestrator with both plugin runtimes initialized.
    pub fn new(app: Arc<AppState>, service_registry: Arc<std::sync::RwLock<ServiceRegistry>>) -> Self {
        Self {
            wasm: WasmPluginManager::new(app.clone()),
            lua: LuaPluginManager::new(app, service_registry),
        }
    }

    /// Scan a directory for plugins (both `.wasm` and `.lua` files).
    pub fn scan_and_load(&mut self, dir: &Path) {
        self.wasm.scan_and_load(dir);
        self.lua.scan_and_load(dir);
    }

    /// Notify all plugins of a state change.
    pub fn notify_state_change(&mut self, entity_id: &str, old_state: &str, new_state: &str) {
        self.wasm.notify_state_change(entity_id, old_state, new_state);
        self.lua.notify_state_change(entity_id, old_state, new_state);
    }

    /// Poll all plugins that implement periodic updates.
    pub fn poll_all(&mut self) {
        self.wasm.poll_all();
        self.lua.poll_all();
    }

    /// Total plugin count across both runtimes.
    pub fn plugin_count(&self) -> usize {
        self.wasm.plugin_count() + self.lua.plugin_count()
    }

    /// Names of all loaded plugins (prefixed with runtime type).
    #[allow(dead_code)]
    pub fn plugin_names(&self) -> Vec<String> {
        let mut names: Vec<String> = self.wasm.plugin_names().into_iter()
            .map(|n| format!("wasm:{}", n))
            .collect();
        names.extend(self.lua.plugin_names().into_iter()
            .map(|n| format!("lua:{}", n)));
        names
    }
}

/// Spawn background tasks for plugin polling and state-change dispatch.
///
/// - Poll task: calls `poll_all()` every 60 seconds
/// - State-change task: subscribes to state_machine events and dispatches
///   `notify_state_change()` for each event
///
/// The orchestrator is wrapped in `Arc<Mutex<>>` because Lua is Send but not Sync.
pub fn spawn_plugin_tasks(
    orchestrator: Arc<Mutex<PluginOrchestrator>>,
    app: Arc<AppState>,
) {
    // Poll loop — every 60 seconds
    let orch_poll = orchestrator.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(60));
        // Skip the first immediate tick
        interval.tick().await;
        loop {
            interval.tick().await;
            let mut orch = orch_poll.lock().await;
            orch.poll_all();
        }
    });

    // State-change listener
    let orch_state = orchestrator;
    let mut rx = app.state_machine.subscribe();
    tokio::spawn(async move {
        loop {
            match rx.recv().await {
                Ok(event) => {
                    let old_state_str = event.old_state
                        .as_ref()
                        .map(|s| s.state.as_str())
                        .unwrap_or("unknown");
                    let new_state_str = event.new_state.state.as_str();
                    let mut orch = orch_state.lock().await;
                    orch.notify_state_change(
                        &event.entity_id,
                        old_state_str,
                        new_state_str,
                    );
                }
                Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => {
                    tracing::warn!("Plugin state-change listener lagged by {} events", n);
                }
                Err(tokio::sync::broadcast::error::RecvError::Closed) => break,
            }
        }
    });
}
