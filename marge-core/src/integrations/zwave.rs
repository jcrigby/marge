#![allow(dead_code)]
//! Z-Wave integration via zwave-js-ui (Phase 2 §2.2)
//!
//! Subscribes to `zwave/#` and provides bridge management:
//! - Node information with Z-Wave command class mapping
//! - Command class → entity domain mapping (CC 37=switch, CC 38=dimmer, etc.)
//! - Commands via `zwave/_CLIENTS/ZWAVE_GATEWAY-<name>/api/writeValue/set`
//! - Inclusion/exclusion workflows
//!
//! Like zigbee2mqtt, zwave-js-ui publishes HA Discovery messages, so basic
//! entity support comes free from discovery.rs. This adds bridge management.

use std::sync::Arc;

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::api::AppState;

/// A Z-Wave node as reported by zwave-js-ui.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ZwaveNode {
    pub id: u32,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub loc: String,
    #[serde(default)]
    pub manufacturer: Option<String>,
    #[serde(default)]
    pub product_description: Option<String>,
    #[serde(default)]
    pub product_label: Option<String>,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub ready: bool,
    #[serde(default)]
    pub interview_stage: Option<String>,
    #[serde(default)]
    pub values: Value,
}

/// Maps Z-Wave command classes to Marge entity domains.
pub fn command_class_to_domain(cc: u32) -> &'static str {
    match cc {
        37 => "switch",         // Binary Switch
        38 => "light",          // Multilevel Switch (dimmer)
        48 => "binary_sensor",  // Sensor Binary
        49 => "sensor",         // Sensor Multilevel
        50 => "sensor",         // Meter
        67 => "climate",        // Thermostat Setpoint
        69 => "climate",        // Thermostat Fan Mode
        64 => "climate",        // Thermostat Mode
        98 => "lock",           // Door Lock
        99 => "lock",           // User Code
        102 => "sensor",        // Barrier Operator
        112 => "number",        // Configuration
        113 => "sensor",        // Notification
        114 => "sensor",        // Manufacturer Specific
        128 => "sensor",        // Battery
        135 => "sensor",        // Indicator
        _ => "sensor",          // Default fallback
    }
}

/// The Z-Wave bridge manager.
pub struct ZwaveBridge {
    /// Known nodes keyed by node_id
    nodes: Arc<DashMap<u32, ZwaveNode>>,
    /// Gateway name (discovered from MQTT topics)
    gateway_name: Arc<std::sync::RwLock<Option<String>>>,
    /// Bridge connected
    connected: Arc<std::sync::atomic::AtomicBool>,
    /// App state for entity creation
    app: Arc<AppState>,
}

impl ZwaveBridge {
    pub fn new(app: Arc<AppState>) -> Self {
        Self {
            nodes: Arc::new(DashMap::new()),
            gateway_name: Arc::new(std::sync::RwLock::new(None)),
            connected: Arc::new(std::sync::atomic::AtomicBool::new(false)),
            app,
        }
    }

    /// Process a message from zwave/#.
    pub fn process_message(&self, topic: &str, payload: &[u8]) {
        let subtopic = match topic.strip_prefix("zwave/") {
            Some(s) => s,
            None => return,
        };

        // Detect gateway name from _CLIENTS topic
        if subtopic.starts_with("_CLIENTS/ZWAVE_GATEWAY-") {
            if let Some(name_end) = subtopic.find("/api/") {
                let name = &subtopic["_CLIENTS/ZWAVE_GATEWAY-".len()..name_end];
                *self.gateway_name.write().unwrap_or_else(|e| e.into_inner()) = Some(name.to_string());
            }
            return;
        }

        // Node status updates: zwave/<node_name>/status
        if subtopic.ends_with("/status") {
            self.handle_node_status(subtopic, payload);
            return;
        }

        // Node list: zwave/_NODES or from the API responses
        if subtopic == "_NODES" {
            self.handle_nodes_list(payload);
            return;
        }

        // Value updates: zwave/<node_name>/<command_class>/<endpoint>/<property>
        let parts: Vec<&str> = subtopic.split('/').collect();
        if parts.len() >= 4 {
            self.handle_value_update(&parts, payload);
        }
    }

    /// Check if a topic belongs to zwave.
    pub fn is_zwave_topic(topic: &str) -> bool {
        topic.starts_with("zwave/")
    }

    /// Build a command topic to set a value on a Z-Wave node.
    pub fn write_value_topic(&self, _node_name: &str, _cc: u32, _endpoint: u32, _property: &str) -> Option<String> {
        let gw = self.gateway_name.read().unwrap_or_else(|e| e.into_inner());
        let gw_name = gw.as_ref()?;
        Some(format!(
            "zwave/_CLIENTS/ZWAVE_GATEWAY-{}/api/writeValue/set",
            gw_name
        ))
    }

    /// Build a writeValue payload for zwave-js-ui.
    pub fn write_value_payload(node_id: u32, cc: u32, endpoint: u32, property: &str, value: Value) -> String {
        serde_json::json!({
            "args": [{
                "nodeId": node_id,
                "commandClass": cc,
                "endpoint": endpoint,
                "property": property,
                "value": value
            }]
        }).to_string()
    }

    /// Build inclusion/exclusion command.
    pub fn inclusion_payload(enable: bool) -> String {
        serde_json::json!({
            "args": [enable]
        }).to_string()
    }

    /// Get all known nodes.
    pub fn nodes(&self) -> Vec<ZwaveNode> {
        self.nodes.iter().map(|e| e.value().clone()).collect()
    }

    /// Get node count.
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    /// Is the bridge connected?
    pub fn is_connected(&self) -> bool {
        self.connected.load(std::sync::atomic::Ordering::Relaxed)
    }

    // ── Private handlers ─────────────────────────────────

    fn handle_node_status(&self, subtopic: &str, payload: &[u8]) {
        let node_name = &subtopic[..subtopic.len() - "/status".len()];
        let payload_str = String::from_utf8_lossy(payload);
        let alive = matches!(
            payload_str.trim().to_lowercase().as_str(),
            "alive" | "true" | "online" | "1"
        );
        tracing::debug!("zwave: node {} status: {} (alive={})", node_name, payload_str.trim(), alive);
    }

    fn handle_nodes_list(&self, payload: &[u8]) {
        let nodes: Vec<ZwaveNode> = match serde_json::from_slice(payload) {
            Ok(n) => n,
            Err(e) => {
                tracing::warn!("zwave: failed to parse nodes list: {}", e);
                return;
            }
        };

        tracing::info!("zwave: received {} nodes", nodes.len());

        for node in nodes {
            let _entity_id = format!(
                "sensor.zwave_node_{}",
                if node.name.is_empty() {
                    format!("{}", node.id)
                } else {
                    node.name.replace([' ', '-'], "_").to_lowercase()
                }
            );

            let mut attrs = serde_json::Map::new();
            attrs.insert("node_id".to_string(), Value::Number(node.id.into()));
            if !node.name.is_empty() {
                attrs.insert("friendly_name".to_string(), Value::String(node.name.clone()));
            }
            if let Some(mfg) = &node.manufacturer {
                attrs.insert("manufacturer".to_string(), Value::String(mfg.clone()));
            }
            if let Some(label) = &node.product_label {
                attrs.insert("product".to_string(), Value::String(label.clone()));
            }
            attrs.insert("ready".to_string(), Value::Bool(node.ready));

            self.nodes.insert(node.id, node);
        }
    }

    fn handle_value_update(&self, parts: &[&str], payload: &[u8]) {
        // parts: [node_name, cc, endpoint, property, ...]
        let payload_str = String::from_utf8_lossy(payload);
        tracing::trace!("zwave: value update {}: {}", parts.join("/"), payload_str);
        // Detailed value processing deferred to the discovery entities
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_bridge() -> ZwaveBridge {
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
        ZwaveBridge::new(app)
    }

    #[test]
    fn test_command_class_mapping() {
        assert_eq!(command_class_to_domain(37), "switch");
        assert_eq!(command_class_to_domain(38), "light");
        assert_eq!(command_class_to_domain(49), "sensor");
        assert_eq!(command_class_to_domain(98), "lock");
        assert_eq!(command_class_to_domain(67), "climate");
        assert_eq!(command_class_to_domain(128), "sensor"); // battery
    }

    #[test]
    fn test_is_zwave_topic() {
        assert!(ZwaveBridge::is_zwave_topic("zwave/node_1/status"));
        assert!(!ZwaveBridge::is_zwave_topic("zigbee2mqtt/bridge/state"));
    }

    #[test]
    fn test_write_value_payload() {
        let payload = ZwaveBridge::write_value_payload(5, 37, 0, "targetValue", Value::Bool(true));
        let parsed: Value = serde_json::from_str(&payload).unwrap();
        assert_eq!(parsed["args"][0]["nodeId"], 5);
        assert_eq!(parsed["args"][0]["commandClass"], 37);
        assert_eq!(parsed["args"][0]["value"], true);
    }

    #[test]
    fn test_nodes_list() {
        let bridge = make_bridge();
        let nodes = serde_json::json!([
            {
                "id": 1,
                "name": "Controller",
                "status": "alive",
                "ready": true,
                "values": {}
            },
            {
                "id": 5,
                "name": "Front Door Lock",
                "manufacturer": "Schlage",
                "product_label": "BE469",
                "status": "alive",
                "ready": true,
                "values": {}
            }
        ]);

        bridge.process_message("zwave/_NODES", serde_json::to_vec(&nodes).unwrap().as_slice());
        assert_eq!(bridge.node_count(), 2);
    }
}
