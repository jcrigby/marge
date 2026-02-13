//! Dynamic service registry (Phase 2 §1.4)
//!
//! Replaces hardcoded match arms in api.rs and automation.rs with a
//! HashMap<(domain, service), ServiceHandler> that supports:
//! - Built-in handlers for known domains (light, switch, lock, climate, etc.)
//! - Discovery-registered handlers (publish to MQTT command_topic)
//! - Automation engine dispatch through the same path

use std::collections::HashMap;
use std::sync::Arc;

use dashmap::DashMap;
use serde_json::Value;
use tokio::sync::mpsc;

use crate::state::StateMachine;

/// The data passed to a service handler when a service is called.
#[derive(Debug, Clone)]
pub struct ServiceCall {
    pub domain: String,
    pub service: String,
    pub entity_id: String,
    pub data: Value,
}

/// A function that handles a service call and returns the new state string
/// (or None if the handler doesn't produce a state change).
pub type ServiceHandlerFn = Box<
    dyn Fn(&ServiceCall, &StateMachine) -> Option<ServiceResult> + Send + Sync,
>;

/// Result of a service handler execution.
pub struct ServiceResult {
    pub state: String,
    pub attributes: serde_json::Map<String, Value>,
}

/// Channel-based handler for MQTT command dispatch.
/// When discovery creates entities, they register a CommandHandler that
/// sends the service call data to an MQTT command_topic.
#[derive(Clone)]
pub struct MqttCommandTarget {
    pub command_topic: String,
    /// Maps service name to the payload to publish.
    /// None means publish the service call data as JSON.
    pub payload_on: Option<String>,
    pub payload_off: Option<String>,
}

/// The service registry.
pub struct ServiceRegistry {
    /// Built-in handlers keyed by (domain, service)
    handlers: HashMap<(String, String), ServiceHandlerFn>,
    /// MQTT command targets keyed by entity_id
    /// These are set by discovery and used to publish commands to MQTT devices.
    mqtt_targets: Arc<DashMap<String, MqttCommandTarget>>,
    /// Channel to send MQTT publish requests
    mqtt_tx: Option<mpsc::UnboundedSender<MqttPublish>>,
}

/// An MQTT publish request from the service registry to the MQTT bridge.
#[derive(Debug, Clone)]
pub struct MqttPublish {
    pub topic: String,
    pub payload: String,
    pub retain: bool,
}

impl ServiceRegistry {
    pub fn new() -> Self {
        let mut registry = Self {
            handlers: HashMap::new(),
            mqtt_targets: Arc::new(DashMap::new()),
            mqtt_tx: None,
        };
        registry.register_builtins();
        registry
    }

    /// Set the MQTT publish channel (called after MQTT broker starts).
    pub fn set_mqtt_tx(&mut self, tx: mpsc::UnboundedSender<MqttPublish>) {
        self.mqtt_tx = Some(tx);
    }

    /// Get a reference to the MQTT targets map (for discovery to register into).
    pub fn mqtt_targets(&self) -> Arc<DashMap<String, MqttCommandTarget>> {
        self.mqtt_targets.clone()
    }

    /// Call a service. Returns the resulting states for affected entities.
    pub fn call(
        &self,
        domain: &str,
        service: &str,
        entity_ids: &[String],
        data: &Value,
        state_machine: &StateMachine,
    ) -> Vec<crate::state::EntityState> {
        let mut changed = Vec::new();

        for eid in entity_ids {
            // First try built-in handler
            let key = (domain.to_string(), service.to_string());
            let call = ServiceCall {
                domain: domain.to_string(),
                service: service.to_string(),
                entity_id: eid.clone(),
                data: data.clone(),
            };

            let result = if let Some(handler) = self.handlers.get(&key) {
                handler(&call, state_machine)
            } else {
                // Fallback: try generic turn_on/turn_off for any domain
                match service {
                    "turn_on" => {
                        let attrs = state_machine
                            .get(eid)
                            .map(|s| s.attributes.clone())
                            .unwrap_or_default();
                        Some(ServiceResult {
                            state: "on".to_string(),
                            attributes: attrs,
                        })
                    }
                    "turn_off" => {
                        let attrs = state_machine
                            .get(eid)
                            .map(|s| s.attributes.clone())
                            .unwrap_or_default();
                        Some(ServiceResult {
                            state: "off".to_string(),
                            attributes: attrs,
                        })
                    }
                    "toggle" => {
                        let current = state_machine.get(eid);
                        let new_state = match current.as_ref().map(|s| s.state.as_str()) {
                            Some("on") => "off",
                            _ => "on",
                        };
                        let attrs = current.map(|s| s.attributes.clone()).unwrap_or_default();
                        Some(ServiceResult {
                            state: new_state.to_string(),
                            attributes: attrs,
                        })
                    }
                    _ => {
                        tracing::warn!("No handler for {}.{}", domain, service);
                        None
                    }
                }
            };

            if let Some(sr) = result {
                let entity_state =
                    state_machine.set(eid.clone(), sr.state, sr.attributes);
                changed.push(entity_state);
            }

            // If there's an MQTT command target for this entity, publish
            self.publish_mqtt_command(&call);
        }

        changed
    }

    /// Publish to the MQTT command_topic for a discovered entity.
    fn publish_mqtt_command(&self, call: &ServiceCall) {
        let tx = match &self.mqtt_tx {
            Some(tx) => tx,
            None => return,
        };

        if let Some(target) = self.mqtt_targets.get(&call.entity_id) {
            let payload = match call.service.as_str() {
                "turn_on" => target
                    .payload_on
                    .clone()
                    .unwrap_or_else(|| "ON".to_string()),
                "turn_off" => target
                    .payload_off
                    .clone()
                    .unwrap_or_else(|| "OFF".to_string()),
                _ => serde_json::to_string(&call.data).unwrap_or_default(),
            };

            let _ = tx.send(MqttPublish {
                topic: target.command_topic.clone(),
                payload,
                retain: false,
            });
        }
    }

    /// Register all built-in service handlers.
    fn register_builtins(&mut self) {
        // ── Light ────────────────────────────────────────
        self.register("light", "turn_on", |call, sm| {
            let mut attrs = sm
                .get(&call.entity_id)
                .map(|s| s.attributes.clone())
                .unwrap_or_default();
            for key in &["brightness", "color_temp", "rgb_color", "xy_color", "hs_color", "effect", "transition"] {
                if let Some(v) = call.data.get(*key) {
                    attrs.insert(key.to_string(), v.clone());
                }
            }
            Some(ServiceResult {
                state: "on".to_string(),
                attributes: attrs,
            })
        });

        self.register("light", "turn_off", |call, sm| {
            let attrs = sm
                .get(&call.entity_id)
                .map(|s| s.attributes.clone())
                .unwrap_or_default();
            Some(ServiceResult {
                state: "off".to_string(),
                attributes: attrs,
            })
        });

        self.register("light", "toggle", |call, sm| {
            let current = sm.get(&call.entity_id);
            let new_state = match current.as_ref().map(|s| s.state.as_str()) {
                Some("on") => "off",
                _ => "on",
            };
            let attrs = current.map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult {
                state: new_state.to_string(),
                attributes: attrs,
            })
        });

        // ── Switch ───────────────────────────────────────
        self.register("switch", "turn_on", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "on".to_string(), attributes: attrs })
        });

        self.register("switch", "turn_off", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "off".to_string(), attributes: attrs })
        });

        self.register("switch", "toggle", |call, sm| {
            let current = sm.get(&call.entity_id);
            let new_state = match current.as_ref().map(|s| s.state.as_str()) {
                Some("on") => "off",
                _ => "on",
            };
            let attrs = current.map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: new_state.to_string(), attributes: attrs })
        });

        // ── Lock ─────────────────────────────────────────
        self.register("lock", "lock", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "locked".to_string(), attributes: attrs })
        });

        self.register("lock", "unlock", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "unlocked".to_string(), attributes: attrs })
        });

        // ── Climate ──────────────────────────────────────
        self.register("climate", "set_temperature", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            if let Some(temp) = call.data.get("temperature") {
                attrs.insert("temperature".to_string(), temp.clone());
            }
            if let Some(target_temp_high) = call.data.get("target_temp_high") {
                attrs.insert("target_temp_high".to_string(), target_temp_high.clone());
            }
            if let Some(target_temp_low) = call.data.get("target_temp_low") {
                attrs.insert("target_temp_low".to_string(), target_temp_low.clone());
            }
            let state_str = sm.get(&call.entity_id).map(|s| s.state.clone()).unwrap_or_else(|| "heat".to_string());
            Some(ServiceResult { state: state_str, attributes: attrs })
        });

        self.register("climate", "set_hvac_mode", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            let mode = call.data.get("hvac_mode").and_then(|v| v.as_str()).unwrap_or("off").to_string();
            Some(ServiceResult { state: mode, attributes: attrs })
        });

        self.register("climate", "set_fan_mode", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            if let Some(fan) = call.data.get("fan_mode") {
                attrs.insert("fan_mode".to_string(), fan.clone());
            }
            let state_str = sm.get(&call.entity_id).map(|s| s.state.clone()).unwrap_or_else(|| "auto".to_string());
            Some(ServiceResult { state: state_str, attributes: attrs })
        });

        // ── Alarm Control Panel ──────────────────────────
        for (svc, state_val) in [
            ("arm_home", "armed_home"),
            ("arm_away", "armed_away"),
            ("arm_night", "armed_night"),
            ("disarm", "disarmed"),
            ("trigger", "triggered"),
        ] {
            let state_owned = state_val.to_string();
            self.register("alarm_control_panel", svc, move |call, sm| {
                let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
                Some(ServiceResult { state: state_owned.clone(), attributes: attrs })
            });
        }

        // ── Cover ────────────────────────────────────────
        self.register("cover", "open_cover", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            attrs.insert("current_position".to_string(), serde_json::json!(100));
            Some(ServiceResult { state: "open".to_string(), attributes: attrs })
        });

        self.register("cover", "close_cover", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            attrs.insert("current_position".to_string(), serde_json::json!(0));
            Some(ServiceResult { state: "closed".to_string(), attributes: attrs })
        });

        self.register("cover", "set_cover_position", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            if let Some(pos) = call.data.get("position") {
                attrs.insert("current_position".to_string(), pos.clone());
            }
            let pos = call.data.get("position").and_then(|v| v.as_i64()).unwrap_or(0);
            let state = if pos > 0 { "open" } else { "closed" };
            Some(ServiceResult { state: state.to_string(), attributes: attrs })
        });

        // ── Fan ──────────────────────────────────────────
        self.register("fan", "turn_on", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            if let Some(pct) = call.data.get("percentage") {
                attrs.insert("percentage".to_string(), pct.clone());
            }
            if let Some(preset) = call.data.get("preset_mode") {
                attrs.insert("preset_mode".to_string(), preset.clone());
            }
            Some(ServiceResult { state: "on".to_string(), attributes: attrs })
        });

        self.register("fan", "turn_off", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "off".to_string(), attributes: attrs })
        });

        self.register("fan", "set_percentage", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            if let Some(pct) = call.data.get("percentage") {
                attrs.insert("percentage".to_string(), pct.clone());
            }
            let pct = call.data.get("percentage").and_then(|v| v.as_i64()).unwrap_or(0);
            let state = if pct > 0 { "on" } else { "off" };
            Some(ServiceResult { state: state.to_string(), attributes: attrs })
        });

        // ── Media Player ─────────────────────────────────
        self.register("media_player", "turn_on", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            if let Some(source) = call.data.get("source") {
                attrs.insert("source".to_string(), source.clone());
            }
            Some(ServiceResult { state: "on".to_string(), attributes: attrs })
        });

        self.register("media_player", "turn_off", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "off".to_string(), attributes: attrs })
        });

        self.register("media_player", "media_play", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "playing".to_string(), attributes: attrs })
        });

        self.register("media_player", "media_pause", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "paused".to_string(), attributes: attrs })
        });

        self.register("media_player", "volume_set", |call, sm| {
            let mut attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            if let Some(vol) = call.data.get("volume_level") {
                attrs.insert("volume_level".to_string(), vol.clone());
            }
            let state = sm.get(&call.entity_id).map(|s| s.state.clone()).unwrap_or_else(|| "on".to_string());
            Some(ServiceResult { state, attributes: attrs })
        });

        // ── Number ───────────────────────────────────────
        self.register("number", "set_value", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            let val = call.data.get("value").map(|v| v.to_string()).unwrap_or_else(|| "0".to_string());
            Some(ServiceResult { state: val, attributes: attrs })
        });

        // ── Select ───────────────────────────────────────
        self.register("select", "select_option", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            let option = call.data.get("option").and_then(|v| v.as_str()).unwrap_or("").to_string();
            Some(ServiceResult { state: option, attributes: attrs })
        });

        // ── Input Helpers ─────────────────────────────────
        self.register("input_number", "set_value", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            let val = call.data.get("value").map(|v| v.to_string()).unwrap_or_else(|| "0".to_string());
            Some(ServiceResult { state: val, attributes: attrs })
        });

        self.register("input_text", "set_value", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            let val = call.data.get("value").and_then(|v| v.as_str()).unwrap_or("").to_string();
            Some(ServiceResult { state: val, attributes: attrs })
        });

        self.register("input_select", "select_option", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            let option = call.data.get("option").and_then(|v| v.as_str()).unwrap_or("").to_string();
            Some(ServiceResult { state: option, attributes: attrs })
        });

        // ── Automation ────────────────────────────────────
        // These are handled specially in api.rs, but registered here for /api/services listing
        self.register("automation", "trigger", |_call, _sm| None);
        self.register("automation", "turn_on", |_call, _sm| None);
        self.register("automation", "turn_off", |_call, _sm| None);
        self.register("automation", "toggle", |_call, _sm| None);

        // ── Scene ───────────────────────────────────────
        self.register("scene", "turn_on", |_call, _sm| None);

        // ── Button ───────────────────────────────────────
        self.register("button", "press", |_call, _sm| {
            // Buttons don't have persistent state; the press is the action
            None
        });

        // ── Siren ────────────────────────────────────────
        self.register("siren", "turn_on", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "on".to_string(), attributes: attrs })
        });

        self.register("siren", "turn_off", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "off".to_string(), attributes: attrs })
        });

        // ── Vacuum ───────────────────────────────────────
        self.register("vacuum", "start", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "cleaning".to_string(), attributes: attrs })
        });

        self.register("vacuum", "stop", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "idle".to_string(), attributes: attrs })
        });

        self.register("vacuum", "return_to_base", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "returning".to_string(), attributes: attrs })
        });

        // ── Valve ────────────────────────────────────────
        self.register("valve", "open_valve", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "open".to_string(), attributes: attrs })
        });

        self.register("valve", "close_valve", |call, sm| {
            let attrs = sm.get(&call.entity_id).map(|s| s.attributes.clone()).unwrap_or_default();
            Some(ServiceResult { state: "closed".to_string(), attributes: attrs })
        });

        // ── Persistent Notification ──────────────────────
        self.register("persistent_notification", "create", |call, _sm| {
            let title = call.data.get("title").and_then(|v| v.as_str()).unwrap_or("");
            let message = call.data.get("message").and_then(|v| v.as_str()).unwrap_or("");
            tracing::info!("NOTIFICATION: {} — {}", title, message);
            None
        });
    }

    /// Register a service handler for (domain, service).
    fn register<F>(&mut self, domain: &str, service: &str, handler: F)
    where
        F: Fn(&ServiceCall, &StateMachine) -> Option<ServiceResult> + Send + Sync + 'static,
    {
        self.handlers
            .insert((domain.to_string(), service.to_string()), Box::new(handler));
    }

    /// Check if a handler exists for a (domain, service) pair.
    pub fn has_handler(&self, domain: &str, service: &str) -> bool {
        self.handlers.contains_key(&(domain.to_string(), service.to_string()))
    }

    /// List all registered services grouped by domain.
    pub fn list_services(&self) -> std::collections::BTreeMap<String, Vec<String>> {
        let mut result: std::collections::BTreeMap<String, Vec<String>> = std::collections::BTreeMap::new();
        for (domain, service) in self.handlers.keys() {
            result.entry(domain.clone()).or_default().push(service.clone());
        }
        for services in result.values_mut() {
            services.sort();
        }
        result
    }

    /// Return services as JSON array matching HA WebSocket format
    pub fn list_domains_json(&self) -> serde_json::Value {
        let services = self.list_services();
        let mut arr = Vec::new();
        for (domain, svcs) in &services {
            let mut svc_map = serde_json::Map::new();
            for svc in svcs {
                svc_map.insert(svc.clone(), serde_json::json!({"description": ""}));
            }
            arr.push(serde_json::json!({
                "domain": domain,
                "services": svc_map,
            }));
        }
        serde_json::Value::Array(arr)
    }
}
