#![allow(dead_code)]
//! HA MQTT Discovery protocol (Phase 2 §1.2)
//!
//! Subscribes to `homeassistant/+/+/config` and `homeassistant/+/+/+/config`
//! and auto-creates entities from discovery payloads.
//!
//! Supports all major component types: sensor, binary_sensor, light, switch,
//! climate, cover, fan, lock, alarm_control_panel, number, select, button,
//! text, scene, siren, vacuum, event, valve, update.
//!
//! Empty payload = entity removal.
//! Device grouping via `device.identifiers`.

use std::sync::Arc;

use dashmap::DashMap;
use serde::Deserialize;
use serde_json::Value;

use crate::api::AppState;
use crate::services::MqttCommandTarget;
use crate::template;

/// A discovered device (groups multiple entities).
#[derive(Debug, Clone)]
pub struct DiscoveredDevice {
    pub identifiers: Vec<String>,
    pub name: Option<String>,
    pub manufacturer: Option<String>,
    pub model: Option<String>,
    pub sw_version: Option<String>,
    pub via_device: Option<String>,
}

/// A discovered entity from an MQTT discovery payload.
#[derive(Debug, Clone)]
pub struct DiscoveredEntity {
    pub entity_id: String,
    pub component: String,
    pub unique_id: String,
    pub name: Option<String>,
    pub device_class: Option<String>,
    pub unit_of_measurement: Option<String>,
    pub state_topic: Option<String>,
    pub command_topic: Option<String>,
    pub availability_topic: Option<String>,
    pub value_template: Option<String>,
    pub payload_on: Option<String>,
    pub payload_off: Option<String>,
    pub device: Option<DiscoveredDevice>,
    /// Full config payload for component-specific fields
    pub config: Value,
}

/// Raw discovery payload (subset of fields we care about).
#[derive(Debug, Deserialize)]
struct DiscoveryPayload {
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    unique_id: Option<String>,
    #[serde(default)]
    object_id: Option<String>,
    #[serde(default)]
    device_class: Option<String>,
    #[serde(default)]
    unit_of_measurement: Option<String>,
    #[serde(default)]
    state_topic: Option<String>,
    #[serde(default)]
    command_topic: Option<String>,
    #[serde(default)]
    availability_topic: Option<String>,
    #[serde(default)]
    availability: Option<Vec<AvailabilityEntry>>,
    #[serde(default)]
    value_template: Option<String>,
    #[serde(default)]
    state_value_template: Option<String>,
    #[serde(default)]
    payload_on: Option<String>,
    #[serde(default)]
    payload_off: Option<String>,
    #[serde(default)]
    device: Option<DevicePayload>,
    // Climate-specific
    #[serde(default)]
    temperature_command_topic: Option<String>,
    #[serde(default)]
    temperature_state_topic: Option<String>,
    #[serde(default)]
    mode_command_topic: Option<String>,
    #[serde(default)]
    mode_state_topic: Option<String>,
    #[serde(default)]
    modes: Option<Vec<String>>,
    // Cover-specific
    #[serde(default)]
    position_topic: Option<String>,
    #[serde(default)]
    set_position_topic: Option<String>,
    // Fan-specific
    #[serde(default)]
    percentage_command_topic: Option<String>,
    #[serde(default)]
    percentage_state_topic: Option<String>,
    // Lock-specific
    #[serde(default)]
    payload_lock: Option<String>,
    #[serde(default)]
    payload_unlock: Option<String>,
}

#[derive(Debug, Deserialize)]
struct AvailabilityEntry {
    topic: String,
    #[serde(default)]
    payload_available: Option<String>,
    #[serde(default)]
    payload_not_available: Option<String>,
}

#[derive(Debug, Deserialize)]
struct DevicePayload {
    #[serde(default)]
    identifiers: StringOrVec,
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    manufacturer: Option<String>,
    #[serde(default)]
    model: Option<String>,
    #[serde(default)]
    sw_version: Option<String>,
    #[serde(default)]
    via_device: Option<String>,
}

#[derive(Debug, Deserialize, Default)]
#[serde(untagged)]
enum StringOrVec {
    Single(String),
    Multiple(Vec<String>),
    #[default]
    None,
}

impl StringOrVec {
    fn to_vec(&self) -> Vec<String> {
        match self {
            StringOrVec::Single(s) => vec![s.clone()],
            StringOrVec::Multiple(v) => v.clone(),
            StringOrVec::None => vec![],
        }
    }
}

/// The discovery engine manages discovered entities and devices.
pub struct DiscoveryEngine {
    /// Discovered entities keyed by entity_id
    entities: Arc<DashMap<String, DiscoveredEntity>>,
    /// Discovered devices keyed by first identifier
    devices: Arc<DashMap<String, DiscoveredDevice>>,
    /// Topics we need to subscribe to (state_topic, availability_topic)
    /// Keyed by topic, value is list of entity_ids interested in this topic
    topic_subscriptions: Arc<DashMap<String, Vec<String>>>,
    /// Reference to app state (owns the state machine)
    app: Arc<AppState>,
    /// MQTT command targets (shared with service registry)
    mqtt_targets: Arc<DashMap<String, MqttCommandTarget>>,
}

impl DiscoveryEngine {
    pub fn new(
        app: Arc<AppState>,
        mqtt_targets: Arc<DashMap<String, MqttCommandTarget>>,
    ) -> Self {
        Self {
            entities: Arc::new(DashMap::new()),
            devices: Arc::new(DashMap::new()),
            topic_subscriptions: Arc::new(DashMap::new()),
            app,
            mqtt_targets,
        }
    }

    /// Process a discovery message.
    /// topic format: homeassistant/{component}/{node_id}/{object_id}/config
    ///           or: homeassistant/{component}/{object_id}/config
    /// Empty payload = remove entity.
    pub fn process_discovery(&self, topic: &str, payload: &[u8]) -> Option<Vec<String>> {
        let parts: Vec<&str> = topic.split('/').collect();
        if parts.len() < 3 || parts[0] != "homeassistant" || *parts.last()? != "config" {
            return None;
        }

        let component = parts[1];

        // Determine object_id based on topic depth
        let (node_id, object_id) = if parts.len() == 4 {
            // homeassistant/{component}/{object_id}/config
            (None, parts[2])
        } else if parts.len() == 5 {
            // homeassistant/{component}/{node_id}/{object_id}/config
            (Some(parts[2]), parts[3])
        } else {
            return None;
        };

        // Empty payload = remove entity
        if payload.is_empty() {
            return self.remove_entity(component, node_id, object_id);
        }

        // Parse discovery payload
        let config: Value = match serde_json::from_slice(payload) {
            Ok(v) => v,
            Err(e) => {
                tracing::warn!("Discovery: invalid JSON from {}: {}", topic, e);
                return None;
            }
        };

        let disc: DiscoveryPayload = match serde_json::from_value(config.clone()) {
            Ok(d) => d,
            Err(e) => {
                tracing::warn!("Discovery: parse error from {}: {}", topic, e);
                return None;
            }
        };

        // Determine entity_id
        let obj_id = disc.object_id.as_deref().unwrap_or(object_id);
        let entity_id = format!("{}.{}", component, obj_id);
        let unique_id = disc
            .unique_id
            .clone()
            .unwrap_or_else(|| format!("{}_{}", node_id.unwrap_or(""), object_id));

        // Build device info
        let device = disc.device.map(|d| DiscoveredDevice {
            identifiers: d.identifiers.to_vec(),
            name: d.name,
            manufacturer: d.manufacturer,
            model: d.model,
            sw_version: d.sw_version,
            via_device: d.via_device,
        });

        // Store device
        if let Some(dev) = &device {
            if let Some(id) = dev.identifiers.first() {
                self.devices.insert(id.clone(), dev.clone());
            }
        }

        // Determine availability topic
        let availability_topic = disc.availability_topic.or_else(|| {
            disc.availability
                .as_ref()
                .and_then(|a| a.first())
                .map(|e| e.topic.clone())
        });

        // Build discovered entity
        let discovered = DiscoveredEntity {
            entity_id: entity_id.clone(),
            component: component.to_string(),
            unique_id,
            name: disc.name,
            device_class: disc.device_class,
            unit_of_measurement: disc.unit_of_measurement.clone(),
            state_topic: disc.state_topic.clone(),
            command_topic: disc.command_topic.clone(),
            availability_topic: availability_topic.clone(),
            value_template: disc.value_template.or(disc.state_value_template),
            payload_on: disc.payload_on.clone(),
            payload_off: disc.payload_off.clone(),
            device,
            config: config.clone(),
        };

        tracing::info!(
            "Discovery: {} ({}) via {}",
            entity_id,
            discovered.name.as_deref().unwrap_or("unnamed"),
            discovered.state_topic.as_deref().unwrap_or("no state topic"),
        );

        // Track topics we need to subscribe to
        let mut new_topics = Vec::new();

        if let Some(st) = &disc.state_topic {
            self.add_topic_subscription(st, &entity_id);
            new_topics.push(st.clone());
        }
        if let Some(at) = &availability_topic {
            self.add_topic_subscription(at, &entity_id);
            new_topics.push(at.clone());
        }
        // Climate has multiple state topics
        if let Some(t) = &disc.temperature_state_topic {
            self.add_topic_subscription(t, &entity_id);
            new_topics.push(t.clone());
        }
        if let Some(t) = &disc.mode_state_topic {
            self.add_topic_subscription(t, &entity_id);
            new_topics.push(t.clone());
        }
        if let Some(t) = &disc.percentage_state_topic {
            self.add_topic_subscription(t, &entity_id);
            new_topics.push(t.clone());
        }
        if let Some(t) = &disc.position_topic {
            self.add_topic_subscription(t, &entity_id);
            new_topics.push(t.clone());
        }

        // Register MQTT command target in service registry
        if let Some(cmd_topic) = &disc.command_topic {
            self.mqtt_targets.insert(
                entity_id.clone(),
                MqttCommandTarget {
                    command_topic: cmd_topic.clone(),
                    payload_on: disc.payload_on,
                    payload_off: disc.payload_off,
                },
            );
        }

        // Create the entity in the state machine
        let mut attrs = serde_json::Map::new();
        if let Some(name) = &discovered.name {
            attrs.insert("friendly_name".to_string(), Value::String(name.clone()));
        }
        if let Some(dc) = &discovered.device_class {
            attrs.insert("device_class".to_string(), Value::String(dc.clone()));
        }
        if let Some(uom) = &disc.unit_of_measurement {
            attrs.insert(
                "unit_of_measurement".to_string(),
                Value::String(uom.clone()),
            );
        }
        // Add component-specific attributes from config
        self.apply_component_attributes(component, &config, &mut attrs);

        let initial_state = match component {
            "binary_sensor" | "sensor" | "event" => "unknown",
            "light" | "switch" | "fan" | "siren" => "off",
            "lock" => "locked",
            "cover" => "closed",
            "climate" => "off",
            "alarm_control_panel" => "disarmed",
            "vacuum" => "docked",
            "valve" => "closed",
            _ => "unknown",
        };

        self.app.state_machine.set(
            entity_id.clone(),
            initial_state.to_string(),
            attrs,
        );

        // Store the discovered entity
        self.entities.insert(entity_id.clone(), discovered);

        Some(new_topics)
    }

    /// Process a state update from an MQTT topic that a discovered entity subscribes to.
    pub fn process_state_update(&self, topic: &str, payload: &[u8]) {
        let payload_str = String::from_utf8_lossy(payload);

        // Find all entities subscribed to this topic
        let entity_ids = match self.topic_subscriptions.get(topic) {
            Some(ids) => ids.clone(),
            None => return,
        };

        for entity_id in &entity_ids {
            if let Some(entity) = self.entities.get(entity_id) {
                // Check if this is an availability topic
                if entity.availability_topic.as_deref() == Some(topic) {
                    self.handle_availability(entity_id, &payload_str);
                    continue;
                }

                // Apply value_template if present
                let state_value = if let Some(tmpl) = &entity.value_template {
                    let ctx = template::TemplateContext::from_payload(&payload_str);
                    match template::render(tmpl, &ctx) {
                        Ok(rendered) => rendered.trim().to_string(),
                        Err(e) => {
                            tracing::warn!(
                                "Discovery: template error for {}: {}",
                                entity_id, e
                            );
                            payload_str.to_string()
                        }
                    }
                } else {
                    // No template — check if it's JSON with a known structure
                    self.extract_state_from_payload(&entity, &payload_str)
                };

                // Update entity state
                let mut attrs = self
                    .app.state_machine
                    .get(entity_id)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();

                // For JSON payloads, merge extra attributes
                if let Ok(Value::Object(map)) = serde_json::from_str::<Value>(&payload_str) {
                    self.merge_json_attributes(&entity, &map, &mut attrs);
                }

                self.app.state_machine
                    .set(entity_id.clone(), state_value, attrs);
            }
        }
    }

    /// Check if a topic is a discovery topic.
    pub fn is_discovery_topic(topic: &str) -> bool {
        topic.starts_with("homeassistant/") && topic.ends_with("/config")
    }

    /// Check if we're subscribed to this topic for state updates.
    pub fn is_subscribed_topic(&self, topic: &str) -> bool {
        self.topic_subscriptions.contains_key(topic)
    }

    /// Get all topics that need MQTT subscriptions.
    pub fn subscribed_topics(&self) -> Vec<String> {
        self.topic_subscriptions
            .iter()
            .map(|e| e.key().clone())
            .collect()
    }

    /// Number of discovered entities.
    pub fn entity_count(&self) -> usize {
        self.entities.len()
    }

    /// Number of discovered devices.
    pub fn device_count(&self) -> usize {
        self.devices.len()
    }

    // ── Private helpers ──────────────────────────────────

    fn add_topic_subscription(&self, topic: &str, entity_id: &str) {
        self.topic_subscriptions
            .entry(topic.to_string())
            .or_default()
            .push(entity_id.to_string());
    }

    fn remove_entity(
        &self,
        component: &str,
        _node_id: Option<&str>,
        object_id: &str,
    ) -> Option<Vec<String>> {
        let entity_id = format!("{}.{}", component, object_id);
        tracing::info!("Discovery: removing {}", entity_id);

        if let Some((_, entity)) = self.entities.remove(&entity_id) {
            // Remove from topic subscriptions
            if let Some(st) = &entity.state_topic {
                self.remove_topic_subscription(st, &entity_id);
            }
            if let Some(at) = &entity.availability_topic {
                self.remove_topic_subscription(at, &entity_id);
            }
            // Remove MQTT command target
            self.mqtt_targets.remove(&entity_id);
            // Set entity state to unavailable
            self.app.state_machine.set(
                entity_id,
                "unavailable".to_string(),
                Default::default(),
            );
        }

        Some(vec![])
    }

    fn remove_topic_subscription(&self, topic: &str, entity_id: &str) {
        if let Some(mut ids) = self.topic_subscriptions.get_mut(topic) {
            ids.retain(|id| id != entity_id);
            if ids.is_empty() {
                drop(ids);
                self.topic_subscriptions.remove(topic);
            }
        }
    }

    fn handle_availability(&self, entity_id: &str, payload: &str) {
        let available = matches!(
            payload.trim().to_lowercase().as_str(),
            "online" | "1" | "true" | "available"
        );
        if !available {
            let attrs = self
                .app.state_machine
                .get(entity_id)
                .map(|s| s.attributes.clone())
                .unwrap_or_default();
            self.app.state_machine
                .set(entity_id.to_string(), "unavailable".to_string(), attrs);
        }
    }

    /// Extract state from a raw payload when no value_template is specified.
    fn extract_state_from_payload(&self, entity: &DiscoveredEntity, payload: &str) -> String {
        // Try JSON first
        if let Ok(json) = serde_json::from_str::<Value>(payload) {
            // Common JSON state fields by component
            match entity.component.as_str() {
                "light" => {
                    if let Some(state) = json.get("state").and_then(|v| v.as_str()) {
                        return state.to_string();
                    }
                }
                "switch" | "binary_sensor" => {
                    if let Some(state) = json.get("state").and_then(|v| v.as_str()) {
                        return state.to_string();
                    }
                }
                "sensor" => {
                    // For sensors, the entire payload might be the value
                    if let Some(state) = json.get("state").and_then(|v| v.as_str()) {
                        return state.to_string();
                    }
                    if let Some(val) = json.get("value") {
                        return match val {
                            Value::String(s) => s.clone(),
                            _ => val.to_string(),
                        };
                    }
                }
                "climate" => {
                    if let Some(mode) = json.get("mode").and_then(|v| v.as_str()) {
                        return mode.to_string();
                    }
                }
                _ => {}
            }
        }

        // Raw payload as-is
        let trimmed = payload.trim();

        // Normalize common ON/OFF variants
        match trimmed.to_uppercase().as_str() {
            "ON" | "TRUE" | "1" => {
                if let Some(pon) = &entity.payload_on {
                    if pon.to_uppercase() == trimmed.to_uppercase() {
                        return match entity.component.as_str() {
                            "binary_sensor" => "on".to_string(),
                            "light" | "switch" | "fan" => "on".to_string(),
                            _ => trimmed.to_string(),
                        };
                    }
                }
                match entity.component.as_str() {
                    "binary_sensor" | "light" | "switch" | "fan" => "on".to_string(),
                    _ => trimmed.to_string(),
                }
            }
            "OFF" | "FALSE" | "0" => {
                match entity.component.as_str() {
                    "binary_sensor" | "light" | "switch" | "fan" => "off".to_string(),
                    _ => trimmed.to_string(),
                }
            }
            _ => trimmed.to_string(),
        }
    }

    /// Merge JSON payload attributes into entity attributes.
    fn merge_json_attributes(
        &self,
        entity: &DiscoveredEntity,
        json: &serde_json::Map<String, Value>,
        attrs: &mut serde_json::Map<String, Value>,
    ) {
        // Merge select fields based on component type
        match entity.component.as_str() {
            "light" => {
                for key in &[
                    "brightness", "color_temp", "color_mode", "rgb_color",
                    "xy_color", "hs_color", "effect",
                ] {
                    if let Some(v) = json.get(*key) {
                        attrs.insert(key.to_string(), v.clone());
                    }
                }
            }
            "climate" => {
                for key in &[
                    "temperature", "current_temperature", "target_temp_high",
                    "target_temp_low", "humidity", "fan_mode", "swing_mode",
                    "preset_mode", "hvac_action",
                ] {
                    if let Some(v) = json.get(*key) {
                        attrs.insert(key.to_string(), v.clone());
                    }
                }
            }
            "fan" => {
                for key in &["percentage", "preset_mode", "direction", "oscillating"] {
                    if let Some(v) = json.get(*key) {
                        attrs.insert(key.to_string(), v.clone());
                    }
                }
            }
            "cover" => {
                for key in &["current_position", "current_tilt_position"] {
                    if let Some(v) = json.get(*key) {
                        attrs.insert(key.to_string(), v.clone());
                    }
                }
            }
            "sensor" => {
                // For sensors, merge any extra keys as attributes
                for (k, v) in json {
                    if k != "state" && k != "value" {
                        attrs.insert(k.clone(), v.clone());
                    }
                }
            }
            _ => {}
        }
    }

    /// Apply component-specific attributes from the config payload.
    fn apply_component_attributes(
        &self,
        component: &str,
        config: &Value,
        attrs: &mut serde_json::Map<String, Value>,
    ) {
        match component {
            "climate" => {
                if let Some(modes) = config.get("modes") {
                    attrs.insert("hvac_modes".to_string(), modes.clone());
                }
                if let Some(min) = config.get("min_temp") {
                    attrs.insert("min_temp".to_string(), min.clone());
                }
                if let Some(max) = config.get("max_temp") {
                    attrs.insert("max_temp".to_string(), max.clone());
                }
                if let Some(step) = config.get("temp_step") {
                    attrs.insert("target_temp_step".to_string(), step.clone());
                }
            }
            "light" => {
                if let Some(modes) = config.get("supported_color_modes") {
                    attrs.insert("supported_color_modes".to_string(), modes.clone());
                }
                if let Some(effects) = config.get("effect_list") {
                    attrs.insert("effect_list".to_string(), effects.clone());
                }
            }
            "fan" => {
                if let Some(speeds) = config.get("speed_range_max") {
                    attrs.insert("speed_count".to_string(), speeds.clone());
                }
                if let Some(presets) = config.get("preset_modes") {
                    attrs.insert("preset_modes".to_string(), presets.clone());
                }
            }
            "cover" => {
                if let Some(dc) = config.get("device_class") {
                    attrs.insert("device_class".to_string(), dc.clone());
                }
            }
            "number" => {
                if let Some(min) = config.get("min") {
                    attrs.insert("min".to_string(), min.clone());
                }
                if let Some(max) = config.get("max") {
                    attrs.insert("max".to_string(), max.clone());
                }
                if let Some(step) = config.get("step") {
                    attrs.insert("step".to_string(), step.clone());
                }
                if let Some(mode) = config.get("mode") {
                    attrs.insert("mode".to_string(), mode.clone());
                }
            }
            "select" => {
                if let Some(options) = config.get("options") {
                    attrs.insert("options".to_string(), options.clone());
                }
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::StateMachine;

    fn make_engine() -> DiscoveryEngine {
        let app = Arc::new(AppState {
            state_machine: StateMachine::new(256),
            started_at: std::time::Instant::now(),
            startup_us: std::sync::atomic::AtomicU64::new(0),
            sim_time: std::sync::Mutex::new(String::new()),
            sim_chapter: std::sync::Mutex::new(String::new()),
            sim_speed: std::sync::atomic::AtomicU32::new(0),
            ws_connections: std::sync::atomic::AtomicU32::new(0),
        });
        let targets = Arc::new(DashMap::new());
        DiscoveryEngine::new(app, targets)
    }

    #[test]
    fn test_basic_sensor_discovery() {
        let engine = make_engine();
        let topic = "homeassistant/sensor/temp1/config";
        let payload = serde_json::json!({
            "name": "Temperature",
            "unique_id": "temp_001",
            "state_topic": "zigbee2mqtt/temp_sensor/state",
            "device_class": "temperature",
            "unit_of_measurement": "°C",
            "value_template": "{{ value_json.temperature }}"
        });

        let topics = engine
            .process_discovery(topic, serde_json::to_vec(&payload).unwrap().as_slice())
            .unwrap();

        assert!(topics.contains(&"zigbee2mqtt/temp_sensor/state".to_string()));
        assert_eq!(engine.entity_count(), 1);

        let state = engine.app.state_machine.get("sensor.temp1").unwrap();
        assert_eq!(state.state, "unknown");
        assert_eq!(
            state.attributes.get("friendly_name").unwrap(),
            &Value::String("Temperature".to_string())
        );
    }

    #[test]
    fn test_light_discovery() {
        let engine = make_engine();
        let topic = "homeassistant/light/living_room/config";
        let payload = serde_json::json!({
            "name": "Living Room Light",
            "unique_id": "lr_light_001",
            "state_topic": "zigbee2mqtt/lr_light/state",
            "command_topic": "zigbee2mqtt/lr_light/set",
            "supported_color_modes": ["brightness", "color_temp"]
        });

        engine.process_discovery(topic, serde_json::to_vec(&payload).unwrap().as_slice());

        let state = engine.app.state_machine.get("light.living_room").unwrap();
        assert_eq!(state.state, "off");
    }

    #[test]
    fn test_entity_removal() {
        let engine = make_engine();
        let topic = "homeassistant/switch/plug1/config";

        // Create
        let payload = serde_json::json!({
            "name": "Smart Plug",
            "unique_id": "plug_001",
            "state_topic": "zigbee2mqtt/plug1/state",
            "command_topic": "zigbee2mqtt/plug1/set"
        });
        engine.process_discovery(topic, serde_json::to_vec(&payload).unwrap().as_slice());
        assert_eq!(engine.entity_count(), 1);

        // Remove (empty payload)
        engine.process_discovery(topic, b"");
        // Entity still exists in state machine (set to unavailable)
        let state = engine.app.state_machine.get("switch.plug1").unwrap();
        assert_eq!(state.state, "unavailable");
    }

    #[test]
    fn test_state_update_with_template() {
        let engine = make_engine();

        // First discover the entity
        let topic = "homeassistant/sensor/temp1/config";
        let payload = serde_json::json!({
            "name": "Temperature",
            "unique_id": "temp_001",
            "state_topic": "sensors/temp1",
            "value_template": "{{ value_json.temperature | round(1) }}"
        });
        engine.process_discovery(topic, serde_json::to_vec(&payload).unwrap().as_slice());

        // Now send a state update
        let state_payload = r#"{"temperature": 22.456, "humidity": 65}"#;
        engine.process_state_update("sensors/temp1", state_payload.as_bytes());

        let state = engine.app.state_machine.get("sensor.temp1").unwrap();
        assert_eq!(state.state, "22.5");
    }

    #[test]
    fn test_node_id_topic_format() {
        let engine = make_engine();
        let topic = "homeassistant/sensor/zigbee2mqtt_bridge/temp1/config";
        let payload = serde_json::json!({
            "name": "Bridge Temp",
            "unique_id": "bridge_temp_001",
            "state_topic": "zigbee2mqtt/bridge/temp"
        });

        engine.process_discovery(topic, serde_json::to_vec(&payload).unwrap().as_slice());
        assert!(engine.app.state_machine.get("sensor.temp1").is_some());
    }
}
