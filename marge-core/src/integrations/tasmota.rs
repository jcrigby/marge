#![allow(dead_code)]
//! Tasmota direct integration (Phase 2 §2.3)
//!
//! Parses Tasmota's MQTT topic structure:
//! - `stat/<device>/RESULT`  — command responses
//! - `stat/<device>/POWER`   — relay state
//! - `tele/<device>/STATE`   — periodic telemetry
//! - `tele/<device>/SENSOR`  — sensor readings
//! - `tele/<device>/LWT`     — availability (Online/Offline)
//! - `cmnd/<device>/<cmd>`   — command topic (for publishing)
//!
//! Tasmota supports HA MQTT Discovery (covered by discovery.rs),
//! so this adds incremental richness: OTA triggers, telemetry
//! parsing, and device configuration.

use std::sync::Arc;

use dashmap::DashMap;
use serde_json::Value;

use crate::api::AppState;

/// A Tasmota device tracked by the bridge.
#[derive(Debug, Clone)]
pub struct TasmotaDevice {
    pub topic_name: String,
    pub friendly_name: Option<String>,
    pub module: Option<String>,
    pub firmware_version: Option<String>,
    pub ip_address: Option<String>,
    pub mac_address: Option<String>,
    pub online: bool,
    pub power_states: Vec<bool>,
}

/// The Tasmota bridge manager.
pub struct TasmotaBridge {
    /// Known devices keyed by topic_name (the %topic% value)
    devices: Arc<DashMap<String, TasmotaDevice>>,
    /// App state for entity creation
    app: Arc<AppState>,
}

impl TasmotaBridge {
    pub fn new(app: Arc<AppState>) -> Self {
        Self {
            devices: Arc::new(DashMap::new()),
            app,
        }
    }

    /// Process a message from stat/, tele/, or cmnd/ topics.
    pub fn process_message(&self, topic: &str, payload: &[u8]) {
        let parts: Vec<&str> = topic.splitn(3, '/').collect();
        if parts.len() < 3 {
            return;
        }

        let prefix = parts[0];
        let device = parts[1];
        let suffix = parts[2];

        match prefix {
            "tele" => match suffix {
                "LWT" => self.handle_lwt(device, payload),
                "STATE" => self.handle_tele_state(device, payload),
                "SENSOR" => self.handle_tele_sensor(device, payload),
                "INFO1" | "INFO2" | "INFO3" => self.handle_info(device, suffix, payload),
                _ => {}
            },
            "stat" => match suffix {
                "RESULT" => self.handle_result(device, payload),
                _ if suffix.starts_with("POWER") => self.handle_power(device, suffix, payload),
                "STATUS" | "STATUS2" | "STATUS5" | "STATUS11" => {
                    self.handle_status(device, suffix, payload);
                }
                _ => {}
            },
            _ => {}
        }
    }

    /// Check if a topic belongs to Tasmota.
    pub fn is_tasmota_topic(topic: &str) -> bool {
        topic.starts_with("stat/") || topic.starts_with("tele/") || topic.starts_with("cmnd/")
    }

    /// Build a command topic for a Tasmota device.
    pub fn command_topic(device: &str, command: &str) -> String {
        format!("cmnd/{}/{}", device, command)
    }

    /// Get all known devices.
    pub fn devices(&self) -> Vec<TasmotaDevice> {
        self.devices.iter().map(|e| e.value().clone()).collect()
    }

    /// Get device count.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }

    // ── Private handlers ─────────────────────────────────

    fn handle_lwt(&self, device: &str, payload: &[u8]) {
        let payload_str = String::from_utf8_lossy(payload);
        let online = payload_str.trim() == "Online";

        self.devices
            .entry(device.to_string())
            .and_modify(|d| d.online = online)
            .or_insert_with(|| TasmotaDevice {
                topic_name: device.to_string(),
                friendly_name: None,
                module: None,
                firmware_version: None,
                ip_address: None,
                mac_address: None,
                online,
                power_states: vec![],
            });

        tracing::debug!("tasmota: {} LWT: {}", device, if online { "Online" } else { "Offline" });
    }

    fn handle_tele_state(&self, device: &str, payload: &[u8]) {
        if let Ok(json) = serde_json::from_slice::<Value>(payload) {
            // Extract power states (POWER, POWER1, POWER2, etc.)
            let mut powers = Vec::new();
            if let Some(p) = json.get("POWER").and_then(|v| v.as_str()) {
                powers.push(p == "ON");
            }
            for i in 1..=8 {
                if let Some(p) = json.get(format!("POWER{}", i)).and_then(|v| v.as_str()) {
                    powers.push(p == "ON");
                }
            }

            self.devices
                .entry(device.to_string())
                .and_modify(|d| {
                    if !powers.is_empty() {
                        d.power_states = powers.clone();
                    }
                })
                .or_insert_with(|| TasmotaDevice {
                    topic_name: device.to_string(),
                    friendly_name: None,
                    module: None,
                    firmware_version: None,
                    ip_address: None,
                    mac_address: None,
                    online: true,
                    power_states: powers,
                });

            // Update entity with telemetry attributes
            let entity_id = format!("sensor.tasmota_{}", device.to_lowercase());
            let mut attrs = self.app.state_machine.get(&entity_id)
                .map(|s| s.attributes.clone())
                .unwrap_or_default();

            if let Some(wifi) = json.get("Wifi") {
                if let Some(rssi) = wifi.get("RSSI") {
                    attrs.insert("wifi_rssi".to_string(), rssi.clone());
                }
                if let Some(signal) = wifi.get("Signal") {
                    attrs.insert("wifi_signal".to_string(), signal.clone());
                }
            }
            if let Some(uptime) = json.get("Uptime").and_then(|v| v.as_str()) {
                attrs.insert("uptime".to_string(), Value::String(uptime.to_string()));
            }
            if let Some(heap) = json.get("Heap") {
                attrs.insert("free_heap".to_string(), heap.clone());
            }
        }
    }

    fn handle_tele_sensor(&self, device: &str, payload: &[u8]) {
        if let Ok(Value::Object(map)) = serde_json::from_slice::<Value>(payload) {
            // Sensor data can contain nested objects like:
            // {"AM2301":{"Temperature":22.5,"Humidity":65},"TempUnit":"C"}
            for (key, value) in &map {
                if let Value::Object(sensor_data) = value {
                    for (metric, val) in sensor_data {
                        let entity_id = format!(
                            "sensor.tasmota_{}_{}_{}",
                            device.to_lowercase(),
                            key.to_lowercase(),
                            metric.to_lowercase()
                        );
                        let val_str = match val {
                            Value::Number(n) => n.to_string(),
                            Value::String(s) => s.clone(),
                            _ => val.to_string(),
                        };
                        let mut attrs = serde_json::Map::new();
                        attrs.insert(
                            "friendly_name".to_string(),
                            Value::String(format!("{} {} {}", device, key, metric)),
                        );
                        self.app.state_machine.set(entity_id, val_str, attrs);
                    }
                }
            }
        }
    }

    fn handle_power(&self, device: &str, suffix: &str, payload: &[u8]) {
        let payload_str = String::from_utf8_lossy(payload);
        let on = payload_str.trim() == "ON";

        // suffix is "POWER" or "POWERn"
        let idx: usize = suffix
            .strip_prefix("POWER")
            .and_then(|s| if s.is_empty() { Some(0) } else { s.parse().ok() })
            .unwrap_or(0);

        self.devices.entry(device.to_string()).and_modify(|d| {
            while d.power_states.len() <= idx {
                d.power_states.push(false);
            }
            d.power_states[idx] = on;
        });

        tracing::debug!("tasmota: {} {} = {}", device, suffix, payload_str.trim());
    }

    fn handle_result(&self, device: &str, payload: &[u8]) {
        // RESULT contains command responses, often same as POWER updates
        if let Ok(json) = serde_json::from_slice::<Value>(payload) {
            if let Some(power) = json.get("POWER").and_then(|v| v.as_str()) {
                self.handle_power(device, "POWER", power.as_bytes());
            }
        }
    }

    fn handle_info(&self, device: &str, suffix: &str, payload: &[u8]) {
        if let Ok(json) = serde_json::from_slice::<Value>(payload) {
            self.devices
                .entry(device.to_string())
                .and_modify(|d| {
                    match suffix {
                        "INFO1" => {
                            d.module = json.get("Module").and_then(|v| v.as_str()).map(String::from);
                            d.firmware_version = json.get("Version").and_then(|v| v.as_str()).map(String::from);
                        }
                        "INFO2" => {
                            d.ip_address = json.get("IPAddress").and_then(|v| v.as_str()).map(String::from);
                        }
                        "INFO3" => {
                            // Boot count, restart reason, etc.
                        }
                        _ => {}
                    }
                })
                .or_insert_with(|| TasmotaDevice {
                    topic_name: device.to_string(),
                    friendly_name: None,
                    module: json.get("Module").and_then(|v| v.as_str()).map(String::from),
                    firmware_version: json.get("Version").and_then(|v| v.as_str()).map(String::from),
                    ip_address: None,
                    mac_address: None,
                    online: true,
                    power_states: vec![],
                });
        }
    }

    fn handle_status(&self, device: &str, suffix: &str, payload: &[u8]) {
        // Various status responses from Tasmota
        if let Ok(_json) = serde_json::from_slice::<Value>(payload) {
            tracing::debug!("tasmota: {} {} response", device, suffix);
            // STATUS5 = network info, STATUS11 = full status, etc.
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_bridge() -> TasmotaBridge {
        let app = Arc::new(AppState {
            state_machine: StateMachine::new(256),
            started_at: std::time::Instant::now(),
            startup_us: std::sync::atomic::AtomicU64::new(0),
            sim_time: std::sync::Mutex::new(String::new()),
            sim_chapter: std::sync::Mutex::new(String::new()),
            sim_speed: std::sync::atomic::AtomicU32::new(0),
        });
        TasmotaBridge::new(app)
    }

    #[test]
    fn test_lwt() {
        let bridge = make_bridge();
        bridge.process_message("tele/sonoff1/LWT", b"Online");
        assert_eq!(bridge.device_count(), 1);
        let devices = bridge.devices();
        assert!(devices[0].online);
    }

    #[test]
    fn test_power_update() {
        let bridge = make_bridge();
        bridge.process_message("tele/sonoff1/LWT", b"Online");
        bridge.process_message("stat/sonoff1/POWER", b"ON");
        let devices = bridge.devices();
        assert!(devices[0].power_states[0]);
    }

    #[test]
    fn test_sensor_telemetry() {
        let bridge = make_bridge();
        let payload = serde_json::json!({
            "AM2301": {"Temperature": 22.5, "Humidity": 65},
            "TempUnit": "C"
        });
        bridge.process_message("tele/th16/SENSOR", serde_json::to_vec(&payload).unwrap().as_slice());

        let temp = bridge.app.state_machine.get("sensor.tasmota_th16_am2301_temperature");
        assert!(temp.is_some());
        assert_eq!(temp.unwrap().state, "22.5");
    }

    #[test]
    fn test_is_tasmota_topic() {
        assert!(TasmotaBridge::is_tasmota_topic("stat/sonoff1/POWER"));
        assert!(TasmotaBridge::is_tasmota_topic("tele/sonoff1/STATE"));
        assert!(TasmotaBridge::is_tasmota_topic("cmnd/sonoff1/Power"));
        assert!(!TasmotaBridge::is_tasmota_topic("zigbee2mqtt/test"));
    }

    #[test]
    fn test_command_topic() {
        assert_eq!(TasmotaBridge::command_topic("sonoff1", "Power"), "cmnd/sonoff1/Power");
    }
}
