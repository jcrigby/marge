//! Matter Sidecar Manager (Phase 7 §7.5)
//!
//! Manages python-matter-server as an external subprocess and communicates
//! via JSON-RPC over WebSocket.  Marge handles entity mapping and state
//! management; the sidecar handles the Thread/BLE commissioning and Matter
//! fabric management.
//!
//! This is NOT a Rust reimplementation of Matter — it's a process manager
//! that delegates to the mature Python implementation.
//!
//! Architecture:
//!   Marge ──WebSocket──► python-matter-server ──Thread/BLE──► Matter devices
//!
//! The sidecar is optional: if python-matter-server is not installed or not
//! running, the integration simply reports "not connected" and creates no
//! entities.  No functionality is lost in the rest of Marge.

use std::collections::HashMap;
use std::sync::Arc;

use dashmap::DashMap;
use serde::{Deserialize, Serialize};

use crate::api::AppState;

// ── Data Structures ─────────────────────────────────────────

/// A Matter device discovered via the sidecar.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatterDevice {
    pub node_id: u64,
    pub name: String,
    pub vendor_name: String,
    pub product_name: String,
    pub device_type: String,
    pub online: bool,
    pub last_seen: String,
    /// Cluster attributes keyed by cluster name
    pub attributes: HashMap<String, serde_json::Value>,
}

/// Connection state to the python-matter-server sidecar.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub enum SidecarStatus {
    /// Not configured or not attempted
    NotConfigured,
    /// Attempting to connect
    Connecting,
    /// Connected and communicating
    Connected,
    /// Connection lost, will retry
    Disconnected,
    /// Sidecar process not found or not running
    NotRunning,
}

/// Configuration for the Matter sidecar connection.
#[derive(Debug, Clone)]
pub struct MatterConfig {
    /// WebSocket URL of the python-matter-server
    pub ws_url: String,
    /// How often to poll for device updates (seconds)
    pub poll_interval_secs: u64,
    /// Whether to auto-start the sidecar process
    pub auto_start: bool,
    /// Path to python-matter-server executable (if auto_start)
    pub sidecar_path: Option<String>,
}

impl Default for MatterConfig {
    fn default() -> Self {
        Self {
            ws_url: std::env::var("MATTER_WS_URL")
                .unwrap_or_else(|_| "ws://localhost:5580/ws".to_string()),
            poll_interval_secs: 10,
            auto_start: false,
            sidecar_path: None,
        }
    }
}

// ── Matter Integration ──────────────────────────────────────

/// The Matter integration manages communication with python-matter-server.
pub struct MatterIntegration {
    pub devices: DashMap<u64, MatterDevice>,
    pub app_state: Arc<AppState>,
    pub config: MatterConfig,
    pub status: std::sync::RwLock<SidecarStatus>,
    pub server_version: std::sync::RwLock<Option<String>>,
}

impl MatterIntegration {
    pub fn new(app_state: Arc<AppState>, config: MatterConfig) -> Self {
        Self {
            devices: DashMap::new(),
            app_state,
            config,
            status: std::sync::RwLock::new(SidecarStatus::NotConfigured),
            server_version: std::sync::RwLock::new(None),
        }
    }

    /// Number of discovered Matter devices.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }

    /// Get current sidecar connection status.
    pub fn get_status(&self) -> SidecarStatus {
        self.status.read().unwrap_or_else(|e| e.into_inner()).clone()
    }

    /// Get sidecar server version if connected.
    pub fn get_server_version(&self) -> Option<String> {
        self.server_version.read().unwrap_or_else(|e| e.into_inner()).clone()
    }

    /// Return all devices as a serializable list.
    pub fn device_list(&self) -> Vec<MatterDevice> {
        self.devices.iter().map(|r| r.value().clone()).collect()
    }

    /// Process a device update from the sidecar and create/update entities.
    pub fn update_device(&self, device: MatterDevice) {
        let node_id = device.node_id;
        let slug = slugify(&device.name);

        // Map Matter device types to Marge entity domains
        let entities = map_device_to_entities(&device, &slug);
        for (entity_id, state, attributes) in entities {
            self.app_state.state_machine.set(entity_id, state, attributes);
        }

        self.devices.insert(node_id, device);
    }

    /// Remove a device and its entities.
    pub fn remove_device(&self, node_id: u64) {
        if let Some((_, device)) = self.devices.remove(&node_id) {
            let slug = slugify(&device.name);
            // Remove entities associated with this device
            let prefixes = [
                format!("light.matter_{}", slug),
                format!("switch.matter_{}", slug),
                format!("sensor.matter_{}", slug),
                format!("binary_sensor.matter_{}", slug),
                format!("lock.matter_{}", slug),
                format!("climate.matter_{}", slug),
                format!("cover.matter_{}", slug),
            ];
            // Note: StateMachine doesn't have a remove method in the current impl,
            // so we set state to "unavailable" instead
            for prefix in &prefixes {
                let mut attrs = serde_json::Map::new();
                attrs.insert("available".into(), serde_json::json!(false));
                self.app_state.state_machine.set(
                    prefix.clone(),
                    "unavailable".to_string(),
                    attrs,
                );
            }
        }
    }

    /// Set the connection status.
    pub fn set_status(&self, status: SidecarStatus) {
        if let Ok(mut s) = self.status.write() {
            *s = status;
        }
    }

    /// Set the server version after successful connection.
    pub fn set_server_version(&self, version: String) {
        if let Ok(mut v) = self.server_version.write() {
            *v = Some(version);
        }
    }
}

// ── Entity Mapping ──────────────────────────────────────────

/// Map a Matter device to Marge entities based on its device type and clusters.
fn map_device_to_entities(
    device: &MatterDevice,
    slug: &str,
) -> Vec<(String, String, serde_json::Map<String, serde_json::Value>)> {
    let mut entities = Vec::new();

    let mut base_attrs = serde_json::Map::new();
    base_attrs.insert("friendly_name".into(), serde_json::json!(device.name));
    base_attrs.insert("integration".into(), serde_json::json!("matter"));
    base_attrs.insert("vendor".into(), serde_json::json!(device.vendor_name));
    base_attrs.insert("product".into(), serde_json::json!(device.product_name));
    base_attrs.insert("node_id".into(), serde_json::json!(device.node_id));
    base_attrs.insert("available".into(), serde_json::json!(device.online));

    match device.device_type.as_str() {
        "on_off_light" | "dimmable_light" | "color_temperature_light" | "extended_color_light" => {
            let mut attrs = base_attrs.clone();
            // Extract brightness if available
            if let Some(level) = device.attributes.get("level_control") {
                if let Some(current) = level.get("current_level") {
                    attrs.insert("brightness".into(), current.clone());
                }
            }
            // Extract on/off state
            let state = device.attributes.get("on_off")
                .and_then(|v| v.get("on_off"))
                .and_then(|v| v.as_bool())
                .map(|on| if on { "on" } else { "off" })
                .unwrap_or("unknown");

            entities.push((
                format!("light.matter_{}", slug),
                state.to_string(),
                attrs,
            ));
        }
        "on_off_plug_in_unit" | "on_off_light_switch" => {
            let attrs = base_attrs.clone();
            let state = device.attributes.get("on_off")
                .and_then(|v| v.get("on_off"))
                .and_then(|v| v.as_bool())
                .map(|on| if on { "on" } else { "off" })
                .unwrap_or("unknown");

            entities.push((
                format!("switch.matter_{}", slug),
                state.to_string(),
                attrs,
            ));
        }
        "door_lock" => {
            let attrs = base_attrs.clone();
            let state = device.attributes.get("door_lock")
                .and_then(|v| v.get("lock_state"))
                .and_then(|v| v.as_u64())
                .map(|s| if s == 1 { "locked" } else { "unlocked" })
                .unwrap_or("unknown");

            entities.push((
                format!("lock.matter_{}", slug),
                state.to_string(),
                attrs,
            ));
        }
        "thermostat" => {
            let mut attrs = base_attrs.clone();
            if let Some(thermo) = device.attributes.get("thermostat") {
                if let Some(temp) = thermo.get("local_temperature") {
                    // Matter temperatures are in 0.01°C units
                    if let Some(raw) = temp.as_f64() {
                        attrs.insert("current_temperature".into(), serde_json::json!(raw / 100.0));
                    }
                }
                if let Some(setpoint) = thermo.get("occupied_heating_setpoint") {
                    if let Some(raw) = setpoint.as_f64() {
                        attrs.insert("temperature".into(), serde_json::json!(raw / 100.0));
                    }
                }
                if let Some(mode) = thermo.get("system_mode") {
                    attrs.insert("hvac_mode".into(), mode.clone());
                }
            }
            attrs.insert("device_class".into(), serde_json::json!("climate"));

            let hvac_mode = attrs.get("hvac_mode")
                .and_then(|v| v.as_str())
                .unwrap_or("off")
                .to_string();

            entities.push((
                format!("climate.matter_{}", slug),
                hvac_mode,
                attrs,
            ));
        }
        "contact_sensor" => {
            let mut attrs = base_attrs.clone();
            attrs.insert("device_class".into(), serde_json::json!("door"));
            let state = device.attributes.get("boolean_state")
                .and_then(|v| v.get("state_value"))
                .and_then(|v| v.as_bool())
                .map(|open| if open { "on" } else { "off" })
                .unwrap_or("unknown");

            entities.push((
                format!("binary_sensor.matter_{}", slug),
                state.to_string(),
                attrs,
            ));
        }
        "occupancy_sensor" => {
            let mut attrs = base_attrs.clone();
            attrs.insert("device_class".into(), serde_json::json!("occupancy"));
            let state = device.attributes.get("occupancy_sensing")
                .and_then(|v| v.get("occupancy"))
                .and_then(|v| v.as_bool())
                .map(|occ| if occ { "on" } else { "off" })
                .unwrap_or("unknown");

            entities.push((
                format!("binary_sensor.matter_{}", slug),
                state.to_string(),
                attrs,
            ));
        }
        "temperature_sensor" => {
            let mut attrs = base_attrs.clone();
            attrs.insert("device_class".into(), serde_json::json!("temperature"));
            attrs.insert("unit_of_measurement".into(), serde_json::json!("°C"));
            let state = device.attributes.get("temperature_measurement")
                .and_then(|v| v.get("measured_value"))
                .and_then(|v| v.as_f64())
                .map(|raw| format!("{:.1}", raw / 100.0))
                .unwrap_or_else(|| "unknown".to_string());

            entities.push((
                format!("sensor.matter_{}", slug),
                state,
                attrs,
            ));
        }
        "window_covering" => {
            let mut attrs = base_attrs.clone();
            if let Some(cover) = device.attributes.get("window_covering") {
                if let Some(pos) = cover.get("current_position_lift_percentage") {
                    attrs.insert("current_position".into(), pos.clone());
                }
            }
            let state = attrs.get("current_position")
                .and_then(|v| v.as_u64())
                .map(|pos| if pos == 0 { "closed" } else { "open" })
                .unwrap_or("unknown")
                .to_string();

            entities.push((
                format!("cover.matter_{}", slug),
                state,
                attrs,
            ));
        }
        _ => {
            // Unknown device type — create a generic sensor showing availability
            let attrs = base_attrs;
            entities.push((
                format!("sensor.matter_{}", slug),
                if device.online { "on" } else { "off" }.to_string(),
                attrs,
            ));
        }
    }

    entities
}

/// Convert a device name to an entity-safe slug.
fn slugify(name: &str) -> String {
    name.to_lowercase()
        .chars()
        .map(|c| if c.is_alphanumeric() { c } else { '_' })
        .collect::<String>()
        .split('_')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("_")
}

// ── Sidecar Poller ──────────────────────────────────────────

/// Start the Matter sidecar connection loop.
///
/// This task attempts to connect to python-matter-server via WebSocket,
/// subscribes to device events, and polls for state updates.  If the
/// connection fails or drops, it retries every `poll_interval_secs`.
///
/// The actual WebSocket communication requires tokio-tungstenite which
/// is already available in the project.  For the initial implementation,
/// we use a simple HTTP-based health check to verify the sidecar is
/// running, and simulate device discovery via the REST API.
pub fn start_matter_poller(integration: Arc<MatterIntegration>, poll_interval_secs: u64) {
    let interval = std::time::Duration::from_secs(poll_interval_secs);

    tokio::spawn(async move {
        // Initial delay to let the sidecar start up
        tokio::time::sleep(std::time::Duration::from_secs(5)).await;

        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(5))
            .build()
            .unwrap_or_default();

        loop {
            // Try to reach the sidecar's HTTP endpoint
            // python-matter-server exposes info at its base URL
            let ws_url = &integration.config.ws_url;
            let http_url = ws_url
                .replace("ws://", "http://")
                .replace("wss://", "https://")
                .replace("/ws", "/info");

            match client.get(&http_url).send().await {
                Ok(resp) if resp.status().is_success() => {
                    if integration.get_status() != SidecarStatus::Connected {
                        integration.set_status(SidecarStatus::Connected);
                        tracing::info!("Matter sidecar connected at {}", ws_url);
                    }

                    // Parse server info if available
                    if let Ok(info) = resp.json::<serde_json::Value>().await {
                        if let Some(version) = info.get("server_version").and_then(|v| v.as_str()) {
                            integration.set_server_version(version.to_string());
                        }
                    }

                    // TODO: Full WebSocket subscription for real-time device events.
                    // For now, the REST API endpoints allow manual device registration
                    // and the poller verifies sidecar connectivity.
                }
                Ok(_) => {
                    if integration.get_status() == SidecarStatus::Connected {
                        tracing::warn!("Matter sidecar returned error — marking disconnected");
                    }
                    integration.set_status(SidecarStatus::Disconnected);
                }
                Err(_) => {
                    let current = integration.get_status();
                    if current == SidecarStatus::Connected {
                        tracing::warn!("Matter sidecar connection lost");
                    }
                    integration.set_status(SidecarStatus::NotRunning);
                }
            }

            tokio::time::sleep(interval).await;
        }
    });
}

// ── Tests ───────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn test_app_state() -> Arc<AppState> {
        Arc::new(AppState {
            state_machine: crate::state::StateMachine::new(128),
            started_at: std::time::Instant::now(),
            startup_us: std::sync::atomic::AtomicU64::new(0),
            sim_time: std::sync::Mutex::new(String::new()),
            sim_chapter: std::sync::Mutex::new(String::new()),
            sim_speed: std::sync::atomic::AtomicU32::new(0),
            ws_connections: std::sync::atomic::AtomicU32::new(0),
            plugin_count: std::sync::atomic::AtomicUsize::new(0),
        })
    }

    #[test]
    fn test_new_integration_empty() {
        let app = test_app_state();
        let config = MatterConfig::default();
        let integration = MatterIntegration::new(app, config);
        assert_eq!(integration.device_count(), 0);
        assert_eq!(integration.get_status(), SidecarStatus::NotConfigured);
        assert!(integration.get_server_version().is_none());
    }

    #[test]
    fn test_device_update_creates_light_entity() {
        let app = test_app_state();
        let config = MatterConfig::default();
        let integration = MatterIntegration::new(app.clone(), config);

        let mut attributes = HashMap::new();
        attributes.insert("on_off".to_string(), serde_json::json!({"on_off": true}));
        attributes.insert("level_control".to_string(), serde_json::json!({"current_level": 200}));

        let device = MatterDevice {
            node_id: 1,
            name: "Kitchen Light".to_string(),
            vendor_name: "IKEA".to_string(),
            product_name: "TRADFRI Bulb".to_string(),
            device_type: "dimmable_light".to_string(),
            online: true,
            last_seen: "2026-02-16T12:00:00Z".to_string(),
            attributes,
        };

        integration.update_device(device);
        assert_eq!(integration.device_count(), 1);

        let state = app.state_machine.get("light.matter_kitchen_light");
        assert!(state.is_some());
        let state = state.unwrap();
        assert_eq!(state.state, "on");
        assert_eq!(state.attributes.get("brightness").and_then(|v| v.as_u64()), Some(200));
    }

    #[test]
    fn test_device_update_creates_switch_entity() {
        let app = test_app_state();
        let config = MatterConfig::default();
        let integration = MatterIntegration::new(app.clone(), config);

        let mut attributes = HashMap::new();
        attributes.insert("on_off".to_string(), serde_json::json!({"on_off": false}));

        let device = MatterDevice {
            node_id: 2,
            name: "Smart Plug".to_string(),
            vendor_name: "Eve".to_string(),
            product_name: "Energy".to_string(),
            device_type: "on_off_plug_in_unit".to_string(),
            online: true,
            last_seen: "2026-02-16T12:00:00Z".to_string(),
            attributes,
        };

        integration.update_device(device);

        let state = app.state_machine.get("switch.matter_smart_plug");
        assert!(state.is_some());
        assert_eq!(state.unwrap().state, "off");
    }

    #[test]
    fn test_device_update_creates_lock_entity() {
        let app = test_app_state();
        let config = MatterConfig::default();
        let integration = MatterIntegration::new(app.clone(), config);

        let mut attributes = HashMap::new();
        attributes.insert("door_lock".to_string(), serde_json::json!({"lock_state": 1}));

        let device = MatterDevice {
            node_id: 3,
            name: "Front Door".to_string(),
            vendor_name: "Yale".to_string(),
            product_name: "Assure Lock 2".to_string(),
            device_type: "door_lock".to_string(),
            online: true,
            last_seen: "2026-02-16T12:00:00Z".to_string(),
            attributes,
        };

        integration.update_device(device);

        let state = app.state_machine.get("lock.matter_front_door");
        assert!(state.is_some());
        assert_eq!(state.unwrap().state, "locked");
    }

    #[test]
    fn test_device_update_creates_thermostat_entity() {
        let app = test_app_state();
        let config = MatterConfig::default();
        let integration = MatterIntegration::new(app.clone(), config);

        let mut attributes = HashMap::new();
        attributes.insert("thermostat".to_string(), serde_json::json!({
            "local_temperature": 2150,
            "occupied_heating_setpoint": 2200,
            "system_mode": "heat"
        }));

        let device = MatterDevice {
            node_id: 4,
            name: "Living Room Thermostat".to_string(),
            vendor_name: "ecobee".to_string(),
            product_name: "SmartThermostat".to_string(),
            device_type: "thermostat".to_string(),
            online: true,
            last_seen: "2026-02-16T12:00:00Z".to_string(),
            attributes,
        };

        integration.update_device(device);

        let state = app.state_machine.get("climate.matter_living_room_thermostat");
        assert!(state.is_some());
        let s = state.unwrap();
        assert_eq!(s.state, "heat");
        assert_eq!(s.attributes.get("current_temperature").and_then(|v| v.as_f64()), Some(21.5));
        assert_eq!(s.attributes.get("temperature").and_then(|v| v.as_f64()), Some(22.0));
    }

    #[test]
    fn test_device_update_creates_temperature_sensor() {
        let app = test_app_state();
        let config = MatterConfig::default();
        let integration = MatterIntegration::new(app.clone(), config);

        let mut attributes = HashMap::new();
        attributes.insert("temperature_measurement".to_string(), serde_json::json!({
            "measured_value": 2350
        }));

        let device = MatterDevice {
            node_id: 5,
            name: "Outdoor Temp".to_string(),
            vendor_name: "Aqara".to_string(),
            product_name: "Temperature Sensor".to_string(),
            device_type: "temperature_sensor".to_string(),
            online: true,
            last_seen: "2026-02-16T12:00:00Z".to_string(),
            attributes,
        };

        integration.update_device(device);

        let state = app.state_machine.get("sensor.matter_outdoor_temp");
        assert!(state.is_some());
        assert_eq!(state.unwrap().state, "23.5");
    }

    #[test]
    fn test_slugify() {
        assert_eq!(slugify("Kitchen Light"), "kitchen_light");
        assert_eq!(slugify("Living Room (Main)"), "living_room_main");
        assert_eq!(slugify("  multiple   spaces  "), "multiple_spaces");
        assert_eq!(slugify("UPPERCASE-dashes"), "uppercase_dashes");
    }

    #[test]
    fn test_status_transitions() {
        let app = test_app_state();
        let config = MatterConfig::default();
        let integration = MatterIntegration::new(app, config);

        assert_eq!(integration.get_status(), SidecarStatus::NotConfigured);
        integration.set_status(SidecarStatus::Connecting);
        assert_eq!(integration.get_status(), SidecarStatus::Connecting);
        integration.set_status(SidecarStatus::Connected);
        assert_eq!(integration.get_status(), SidecarStatus::Connected);
        integration.set_server_version("1.5.0".to_string());
        assert_eq!(integration.get_server_version(), Some("1.5.0".to_string()));
    }
}
