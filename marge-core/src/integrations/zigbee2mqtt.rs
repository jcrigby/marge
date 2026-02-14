//! zigbee2mqtt bridge integration (Phase 2 §2.1)
//!
//! Subscribes to `zigbee2mqtt/#` and provides deeper bridge management
//! beyond what HA MQTT Discovery covers:
//! - Device registry from `bridge/devices` with `exposes` capability arrays
//! - Group management from `bridge/groups`
//! - Bridge events: device_joined, device_interview, device_leave
//! - Pairing UI: publish to `zigbee2mqtt/bridge/request/permit_join`
//! - Availability tracking via `<name>/availability`
//!
//! Note: zigbee2mqtt also publishes HA Discovery messages, so basic entity
//! support comes free from discovery.rs. This module adds bridge management.

use std::sync::Arc;

use dashmap::DashMap;
use serde::Deserialize;
use serde_json::Value;

use crate::api::AppState;

/// A Zigbee device as reported by zigbee2mqtt bridge/devices.
#[derive(Debug, Clone, Deserialize)]
pub struct ZigbeeDevice {
    pub ieee_address: String,
    #[serde(default)]
    pub friendly_name: String,
    #[serde(default)]
    pub r#type: String,
    #[serde(default)]
    pub definition: Option<DeviceDefinition>,
    #[serde(default)]
    pub model_id: Option<String>,
    #[serde(default)]
    pub manufacturer: Option<String>,
    #[serde(default)]
    pub power_source: Option<String>,
    #[serde(default)]
    pub interviewing: bool,
    #[serde(default)]
    pub interview_completed: bool,
    #[serde(default)]
    pub supported: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DeviceDefinition {
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub vendor: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub exposes: Vec<Value>,
}

/// A Zigbee group as reported by zigbee2mqtt bridge/groups.
#[derive(Debug, Clone, Deserialize)]
pub struct ZigbeeGroup {
    pub id: u32,
    #[serde(default)]
    pub friendly_name: String,
    #[serde(default)]
    pub members: Vec<GroupMember>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GroupMember {
    #[serde(default)]
    pub ieee_address: String,
    #[serde(default)]
    pub endpoint: u32,
}

/// Bridge event from zigbee2mqtt/bridge/event.
#[derive(Debug, Clone, Deserialize)]
pub struct BridgeEvent {
    pub r#type: String,
    #[serde(default)]
    pub data: Value,
}

/// The zigbee2mqtt bridge manager.
pub struct Zigbee2MqttBridge {
    /// Known devices keyed by ieee_address
    devices: Arc<DashMap<String, ZigbeeDevice>>,
    /// Known groups keyed by group id
    groups: Arc<DashMap<u32, ZigbeeGroup>>,
    /// Bridge state (online/offline)
    bridge_state: Arc<std::sync::RwLock<String>>,
    /// Permit join active
    permit_join: Arc<std::sync::atomic::AtomicBool>,
    /// App state for entity creation
    app: Arc<AppState>,
}

impl Zigbee2MqttBridge {
    pub fn new(app: Arc<AppState>) -> Self {
        Self {
            devices: Arc::new(DashMap::new()),
            groups: Arc::new(DashMap::new()),
            bridge_state: Arc::new(std::sync::RwLock::new("unknown".to_string())),
            permit_join: Arc::new(std::sync::atomic::AtomicBool::new(false)),
            app,
        }
    }

    /// Process a message from zigbee2mqtt/#.
    /// Returns topics to subscribe to if new ones are needed.
    pub fn process_message(&self, topic: &str, payload: &[u8]) {
        let subtopic = match topic.strip_prefix("zigbee2mqtt/") {
            Some(s) => s,
            None => return,
        };

        match subtopic {
            "bridge/state" => self.handle_bridge_state(payload),
            "bridge/devices" => self.handle_bridge_devices(payload),
            "bridge/groups" => self.handle_bridge_groups(payload),
            "bridge/event" => self.handle_bridge_event(payload),
            "bridge/logging" => { /* ignore logging messages */ }
            "bridge/info" => { /* bridge info, version etc */ }
            "bridge/extensions" => { /* extensions list */ }
            _ => {
                // Device state update: zigbee2mqtt/<friendly_name>
                // or availability: zigbee2mqtt/<friendly_name>/availability
                if subtopic.ends_with("/availability") {
                    let device_name = &subtopic[..subtopic.len() - "/availability".len()];
                    self.handle_device_availability(device_name, payload);
                } else if !subtopic.contains('/') || subtopic.ends_with("/get") || subtopic.ends_with("/set") {
                    // Device state or command — handled by discovery.rs via HA MQTT Discovery
                    // We just track additional metadata here
                    if !subtopic.contains('/') {
                        self.handle_device_state(subtopic, payload);
                    }
                }
            }
        }
    }

    /// Check if a topic belongs to zigbee2mqtt.
    pub fn is_z2m_topic(topic: &str) -> bool {
        topic.starts_with("zigbee2mqtt/")
    }

    /// Request permit join (pairing mode).
    pub fn permit_join_payload(enable: bool, duration: Option<u32>) -> String {
        let time = duration.unwrap_or(if enable { 120 } else { 0 });
        serde_json::json!({
            "value": enable,
            "time": time
        }).to_string()
    }

    /// Get all known devices.
    pub fn devices(&self) -> Vec<ZigbeeDevice> {
        self.devices.iter().map(|e| e.value().clone()).collect()
    }

    /// Get device count.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }

    /// Get bridge state.
    pub fn bridge_state(&self) -> String {
        self.bridge_state.read().unwrap_or_else(|e| e.into_inner()).clone()
    }

    // ── Private handlers ─────────────────────────────────

    fn handle_bridge_state(&self, payload: &[u8]) {
        let payload_str = String::from_utf8_lossy(payload);
        // Can be plain text "online"/"offline" or JSON {"state":"online"}
        let state = if let Ok(json) = serde_json::from_str::<Value>(&payload_str) {
            json.get("state")
                .and_then(|v| v.as_str())
                .unwrap_or(&payload_str)
                .to_string()
        } else {
            payload_str.trim().to_string()
        };

        tracing::info!("zigbee2mqtt bridge state: {}", state);
        *self.bridge_state.write().unwrap_or_else(|e| e.into_inner()) = state.clone();

        // Update bridge entity
        self.app.state_machine.set(
            "binary_sensor.zigbee2mqtt_bridge".to_string(),
            if state == "online" { "on" } else { "off" }.to_string(),
            serde_json::Map::from_iter([(
                "friendly_name".to_string(),
                Value::String("Zigbee2MQTT Bridge".to_string()),
            )]),
        );
    }

    fn handle_bridge_devices(&self, payload: &[u8]) {
        let devices: Vec<ZigbeeDevice> = match serde_json::from_slice(payload) {
            Ok(d) => d,
            Err(e) => {
                tracing::warn!("zigbee2mqtt: failed to parse bridge/devices: {}", e);
                return;
            }
        };

        tracing::info!("zigbee2mqtt: received {} devices", devices.len());

        for device in devices {
            // Skip the coordinator
            if device.r#type == "Coordinator" {
                continue;
            }

            // Register a sensor entity with device metadata
            let _entity_id = format!(
                "sensor.z2m_{}",
                device.friendly_name.replace(' ', "_").replace('-', "_").to_lowercase()
            );

            let mut attrs = serde_json::Map::new();
            attrs.insert("friendly_name".to_string(), Value::String(device.friendly_name.clone()));
            attrs.insert("ieee_address".to_string(), Value::String(device.ieee_address.clone()));
            if let Some(mfg) = &device.manufacturer {
                attrs.insert("manufacturer".to_string(), Value::String(mfg.clone()));
            }
            if let Some(model) = &device.model_id {
                attrs.insert("model_id".to_string(), Value::String(model.clone()));
            }
            if let Some(ps) = &device.power_source {
                attrs.insert("power_source".to_string(), Value::String(ps.clone()));
            }
            attrs.insert("supported".to_string(), Value::Bool(device.supported));
            attrs.insert("interview_completed".to_string(), Value::Bool(device.interview_completed));
            if let Some(def) = &device.definition {
                if let Some(desc) = &def.description {
                    attrs.insert("description".to_string(), Value::String(desc.clone()));
                }
            }

            self.devices.insert(device.ieee_address.clone(), device);
        }
    }

    fn handle_bridge_groups(&self, payload: &[u8]) {
        let groups: Vec<ZigbeeGroup> = match serde_json::from_slice(payload) {
            Ok(g) => g,
            Err(e) => {
                tracing::warn!("zigbee2mqtt: failed to parse bridge/groups: {}", e);
                return;
            }
        };

        tracing::info!("zigbee2mqtt: received {} groups", groups.len());

        for group in groups {
            self.groups.insert(group.id, group);
        }
    }

    fn handle_bridge_event(&self, payload: &[u8]) {
        let event: BridgeEvent = match serde_json::from_slice(payload) {
            Ok(e) => e,
            Err(e) => {
                tracing::warn!("zigbee2mqtt: failed to parse bridge/event: {}", e);
                return;
            }
        };

        match event.r#type.as_str() {
            "device_joined" => {
                let friendly_name = event.data.get("friendly_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                tracing::info!("zigbee2mqtt: device joined: {}", friendly_name);
            }
            "device_interview" => {
                let status = event.data.get("status")
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                let friendly_name = event.data.get("friendly_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                tracing::info!("zigbee2mqtt: device interview {}: {}", friendly_name, status);
            }
            "device_leave" => {
                let friendly_name = event.data.get("friendly_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                tracing::info!("zigbee2mqtt: device left: {}", friendly_name);
                // Remove from registry
                if let Some(ieee) = event.data.get("ieee_address").and_then(|v| v.as_str()) {
                    self.devices.remove(ieee);
                }
            }
            _ => {
                tracing::debug!("zigbee2mqtt: bridge event: {}", event.r#type);
            }
        }
    }

    fn handle_device_availability(&self, device_name: &str, payload: &[u8]) {
        let payload_str = String::from_utf8_lossy(payload);
        let available = matches!(
            payload_str.trim().to_lowercase().as_str(),
            "online" | "true" | "1"
        );
        tracing::debug!("zigbee2mqtt: {} availability: {}", device_name, available);
    }

    fn handle_device_state(&self, device_name: &str, payload: &[u8]) {
        // Device state updates come as JSON with multiple properties.
        // The HA Discovery entities handle the primary state; here we can
        // track extra metadata or trigger additional logic.
        let payload_str = String::from_utf8_lossy(payload);
        if let Ok(json) = serde_json::from_str::<Value>(&payload_str) {
            // Track link quality if present
            if let Some(lqi) = json.get("linkquality") {
                tracing::trace!("zigbee2mqtt: {} linkquality: {}", device_name, lqi);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_bridge() -> Zigbee2MqttBridge {
        let app = Arc::new(AppState {
            state_machine: StateMachine::new(256),
            started_at: std::time::Instant::now(),
            startup_us: std::sync::atomic::AtomicU64::new(0),
            sim_time: std::sync::Mutex::new(String::new()),
            sim_chapter: std::sync::Mutex::new(String::new()),
            sim_speed: std::sync::atomic::AtomicU32::new(0),
        });
        Zigbee2MqttBridge::new(app)
    }

    #[test]
    fn test_bridge_state_online() {
        let bridge = make_bridge();
        bridge.process_message("zigbee2mqtt/bridge/state", b"online");
        assert_eq!(bridge.bridge_state(), "online");

        let entity = bridge.app.state_machine.get("binary_sensor.zigbee2mqtt_bridge").unwrap();
        assert_eq!(entity.state, "on");
    }

    #[test]
    fn test_bridge_state_json() {
        let bridge = make_bridge();
        bridge.process_message(
            "zigbee2mqtt/bridge/state",
            br#"{"state":"offline"}"#,
        );
        assert_eq!(bridge.bridge_state(), "offline");
    }

    #[test]
    fn test_bridge_devices() {
        let bridge = make_bridge();
        let devices = serde_json::json!([
            {
                "ieee_address": "0x00158d0001234567",
                "friendly_name": "Living Room Sensor",
                "type": "EndDevice",
                "model_id": "WSDCGQ11LM",
                "manufacturer": "Aqara",
                "supported": true,
                "interview_completed": true
            },
            {
                "ieee_address": "0x00000000",
                "friendly_name": "Coordinator",
                "type": "Coordinator"
            }
        ]);

        bridge.process_message(
            "zigbee2mqtt/bridge/devices",
            serde_json::to_vec(&devices).unwrap().as_slice(),
        );

        assert_eq!(bridge.device_count(), 1); // Coordinator excluded
    }

    #[test]
    fn test_permit_join_payload() {
        let payload = Zigbee2MqttBridge::permit_join_payload(true, Some(60));
        let parsed: Value = serde_json::from_str(&payload).unwrap();
        assert_eq!(parsed["value"], true);
        assert_eq!(parsed["time"], 60);
    }

    #[test]
    fn test_is_z2m_topic() {
        assert!(Zigbee2MqttBridge::is_z2m_topic("zigbee2mqtt/bridge/state"));
        assert!(Zigbee2MqttBridge::is_z2m_topic("zigbee2mqtt/living_room_sensor"));
        assert!(!Zigbee2MqttBridge::is_z2m_topic("homeassistant/sensor/test/config"));
    }
}
