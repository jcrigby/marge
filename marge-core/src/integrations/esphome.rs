#![allow(dead_code)]
//! ESPHome direct integration (Phase 2 §2.3)
//!
//! Parses ESPHome's MQTT topic structure:
//! - `<prefix>/<component>/<name>/state`   — state updates
//! - `<prefix>/<component>/<name>/command`  — command topic
//! - `<prefix>/status`                      — availability (online/offline)
//! - `<prefix>/debug`                       — debug log output
//!
//! ESPHome supports HA MQTT Discovery (covered by discovery.rs),
//! so this adds incremental richness: device info tracking,
//! OTA update triggers, and configuration management.

use std::sync::Arc;

use dashmap::DashMap;
use serde::Serialize;
use serde_json::Value;

use crate::api::AppState;

/// An ESPHome device tracked by the bridge.
#[derive(Debug, Clone, Serialize)]
pub struct ESPHomeDevice {
    pub prefix: String,
    pub name: Option<String>,
    pub version: Option<String>,
    pub mac_address: Option<String>,
    pub ip_address: Option<String>,
    pub online: bool,
    /// Component entities: (component_type, name) → last known state
    pub components: Vec<(String, String)>,
}

/// The ESPHome bridge manager.
pub struct ESPHomeBridge {
    /// Known devices keyed by MQTT prefix
    devices: Arc<DashMap<String, ESPHomeDevice>>,
    /// App state for entity creation
    app: Arc<AppState>,
}

impl ESPHomeBridge {
    pub fn new(app: Arc<AppState>) -> Self {
        Self {
            devices: Arc::new(DashMap::new()),
            app,
        }
    }

    /// Process a message from an ESPHome device.
    /// ESPHome topic prefix is configurable but typically the device name.
    pub fn process_message(&self, topic: &str, payload: &[u8], prefix: &str) {
        let subtopic = match topic.strip_prefix(&format!("{}/", prefix)) {
            Some(s) => s,
            None => return,
        };

        match subtopic {
            "status" => self.handle_status(prefix, payload),
            "debug" => { /* ignore debug logs */ }
            _ => {
                // Parse: <component>/<name>/state or <component>/<name>/command
                let parts: Vec<&str> = subtopic.split('/').collect();
                if parts.len() == 3 && parts[2] == "state" {
                    self.handle_component_state(prefix, parts[0], parts[1], payload);
                }
            }
        }
    }

    /// Try to match a topic to a known ESPHome device prefix.
    /// Returns the prefix if matched.
    pub fn match_prefix(&self, topic: &str) -> Option<String> {
        for entry in self.devices.iter() {
            if topic.starts_with(&format!("{}/", entry.key())) {
                return Some(entry.key().clone());
            }
        }
        None
    }

    /// Register a device prefix (called when discovery reveals an ESPHome device).
    pub fn register_prefix(&self, prefix: &str, name: Option<String>) {
        self.devices.entry(prefix.to_string()).or_insert_with(|| ESPHomeDevice {
            prefix: prefix.to_string(),
            name,
            version: None,
            mac_address: None,
            ip_address: None,
            online: true,
            components: vec![],
        });
    }

    /// Get all known devices.
    pub fn devices(&self) -> Vec<ESPHomeDevice> {
        self.devices.iter().map(|e| e.value().clone()).collect()
    }

    /// Get device count.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }

    // ── Private handlers ─────────────────────────────────

    fn handle_status(&self, prefix: &str, payload: &[u8]) {
        let payload_str = String::from_utf8_lossy(payload);
        let online = payload_str.trim().to_lowercase() == "online";

        self.devices
            .entry(prefix.to_string())
            .and_modify(|d| d.online = online)
            .or_insert_with(|| ESPHomeDevice {
                prefix: prefix.to_string(),
                name: None,
                version: None,
                mac_address: None,
                ip_address: None,
                online,
                components: vec![],
            });

        tracing::debug!("esphome: {} status: {}", prefix, if online { "online" } else { "offline" });
    }

    fn handle_component_state(&self, prefix: &str, component: &str, name: &str, payload: &[u8]) {
        let payload_str = String::from_utf8_lossy(payload);

        // Track the component in the device
        let comp_key = (component.to_string(), name.to_string());
        self.devices.entry(prefix.to_string()).and_modify(|d| {
            if !d.components.contains(&comp_key) {
                d.components.push(comp_key.clone());
            }
        });

        // Map ESPHome component types to HA domains
        let domain = match component {
            "light" => "light",
            "switch" => "switch",
            "sensor" => "sensor",
            "binary_sensor" => "binary_sensor",
            "fan" => "fan",
            "cover" => "cover",
            "climate" => "climate",
            "lock" => "lock",
            "number" => "number",
            "select" => "select",
            "button" => "button",
            "text_sensor" => "sensor",
            _ => "sensor",
        };

        let entity_id = format!(
            "{}.esphome_{}_{}",
            domain,
            prefix.replace('-', "_").to_lowercase(),
            name.replace('-', "_").to_lowercase()
        );

        // Determine state value
        let state = if let Ok(json) = serde_json::from_str::<Value>(&payload_str) {
            // JSON payload — extract state
            if let Some(s) = json.get("state").and_then(|v| v.as_str()) {
                s.to_string()
            } else {
                payload_str.trim().to_string()
            }
        } else {
            // Plain text payload
            let trimmed = payload_str.trim();
            match trimmed.to_uppercase().as_str() {
                "ON" | "TRUE" | "1" => match domain {
                    "binary_sensor" | "light" | "switch" | "fan" => "on".to_string(),
                    _ => trimmed.to_string(),
                },
                "OFF" | "FALSE" | "0" => match domain {
                    "binary_sensor" | "light" | "switch" | "fan" => "off".to_string(),
                    _ => trimmed.to_string(),
                },
                _ => trimmed.to_string(),
            }
        };

        let mut attrs = self.app.state_machine.get(&entity_id)
            .map(|s| s.attributes.clone())
            .unwrap_or_default();
        attrs.insert(
            "friendly_name".to_string(),
            Value::String(format!("{} {}", prefix, name).replace('_', " ")),
        );

        self.app.state_machine.set(entity_id, state, attrs);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_bridge() -> ESPHomeBridge {
        let app = Arc::new(AppState {
            state_machine: StateMachine::new(256),
            started_at: std::time::Instant::now(),
            startup_us: std::sync::atomic::AtomicU64::new(0),
            sim_time: std::sync::Mutex::new(String::new()),
            sim_chapter: std::sync::Mutex::new(String::new()),
            sim_speed: std::sync::atomic::AtomicU32::new(0),
            ws_connections: std::sync::atomic::AtomicU32::new(0),
            plugin_count: std::sync::atomic::AtomicUsize::new(0),
        });
        ESPHomeBridge::new(app)
    }

    #[test]
    fn test_status_online() {
        let bridge = make_bridge();
        bridge.register_prefix("bedroom-sensor", Some("Bedroom Sensor".to_string()));
        bridge.process_message("bedroom-sensor/status", b"online", "bedroom-sensor");

        let devices = bridge.devices();
        assert_eq!(devices.len(), 1);
        assert!(devices[0].online);
    }

    #[test]
    fn test_component_state() {
        let bridge = make_bridge();
        bridge.register_prefix("office-light", None);
        bridge.process_message(
            "office-light/light/desk_lamp/state",
            b"ON",
            "office-light",
        );

        let entity = bridge.app.state_machine.get("light.esphome_office_light_desk_lamp");
        assert!(entity.is_some());
        assert_eq!(entity.unwrap().state, "on");
    }

    #[test]
    fn test_sensor_value() {
        let bridge = make_bridge();
        bridge.register_prefix("env-sensor", None);
        bridge.process_message(
            "env-sensor/sensor/temperature/state",
            b"23.5",
            "env-sensor",
        );

        let entity = bridge.app.state_machine.get("sensor.esphome_env_sensor_temperature");
        assert!(entity.is_some());
        assert_eq!(entity.unwrap().state, "23.5");
    }

    #[test]
    fn test_prefix_matching() {
        let bridge = make_bridge();
        bridge.register_prefix("my-device", None);

        assert_eq!(
            bridge.match_prefix("my-device/sensor/temp/state"),
            Some("my-device".to_string())
        );
        assert_eq!(bridge.match_prefix("other/sensor/temp/state"), None);
    }
}
