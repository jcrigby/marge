use serde::Deserialize;
use std::path::Path;
use std::sync::Arc;

use crate::api::AppState;
use crate::scene::SceneEngine;
use crate::state::StateChangedEvent;

// ── YAML Deserialization Structs ─────────────────────────

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct Automation {
    pub id: String,
    #[serde(default)]
    pub alias: String,
    #[serde(default)]
    pub description: String,
    #[serde(default = "default_mode")]
    pub mode: String,
    #[serde(default)]
    pub triggers: Vec<Trigger>,
    #[serde(default)]
    pub conditions: Vec<Condition>,
    #[serde(default)]
    pub actions: Vec<Action>,
}

fn default_mode() -> String {
    "single".to_string()
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "trigger")]
#[allow(dead_code)]
pub enum Trigger {
    #[serde(rename = "state")]
    State {
        entity_id: StringOrVec,
        #[serde(default)]
        to: Option<String>,
        #[serde(default)]
        from: Option<String>,
    },
    #[serde(rename = "time")]
    Time {
        at: String,
    },
    #[serde(rename = "sun")]
    Sun {
        event: String, // "sunrise" or "sunset"
    },
    #[serde(rename = "event")]
    Event {
        event_type: String,
    },
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "condition")]
pub enum Condition {
    #[serde(rename = "state")]
    State {
        entity_id: String,
        state: String,
    },
    #[serde(rename = "or")]
    Or {
        conditions: Vec<Condition>,
    },
    #[serde(rename = "and")]
    And {
        conditions: Vec<Condition>,
    },
}

#[derive(Debug, Clone, Deserialize)]
pub struct Action {
    pub action: String, // "light.turn_on", "lock.lock", etc.
    #[serde(default)]
    pub target: Option<ActionTarget>,
    #[serde(default)]
    pub data: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ActionTarget {
    #[serde(default)]
    pub entity_id: Option<StringOrVec>,
}

/// Handles YAML values that can be a single string or a list of strings.
#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum StringOrVec {
    Single(String),
    Multiple(Vec<String>),
}

impl StringOrVec {
    pub fn to_vec(&self) -> Vec<String> {
        match self {
            StringOrVec::Single(s) => vec![s.clone()],
            StringOrVec::Multiple(v) => v.clone(),
        }
    }
}

// ── Parser ───────────────────────────────────────────────

pub fn load_automations(path: &Path) -> anyhow::Result<Vec<Automation>> {
    let contents = std::fs::read_to_string(path)?;
    let automations: Vec<Automation> = serde_yaml::from_str(&contents)?;
    Ok(automations)
}

// ── Engine ───────────────────────────────────────────────

pub struct AutomationEngine {
    automations: Vec<Automation>,
    app: Arc<AppState>,
    scenes: Option<Arc<SceneEngine>>,
}

impl AutomationEngine {
    pub fn new(automations: Vec<Automation>, app: Arc<AppState>) -> Self {
        tracing::info!("Loaded {} automations", automations.len());
        for auto in &automations {
            tracing::info!("  [{}] {} — {} trigger(s), {} condition(s), {} action(s)",
                auto.id, auto.alias,
                auto.triggers.len(), auto.conditions.len(), auto.actions.len());
        }
        Self { automations, app, scenes: None }
    }

    pub fn set_scenes(&mut self, scenes: Arc<SceneEngine>) {
        self.scenes = Some(scenes);
    }

    /// Evaluate a state_changed event against all automations.
    /// Returns the IDs of automations that fired.
    pub async fn on_state_changed(&self, event: &StateChangedEvent) -> Vec<String> {
        let mut fired = Vec::new();

        for auto in &self.automations {
            if self.triggers_match(auto, event) && self.conditions_met(auto) {
                tracing::info!("Automation [{}] triggered by {}", auto.id, event.entity_id);
                self.execute_actions(auto).await;
                fired.push(auto.id.clone());
            }
        }

        fired
    }

    /// Force-trigger an automation by ID (bypasses triggers and conditions).
    /// Used by automation.trigger service call.
    pub async fn trigger_by_id(&self, automation_id: &str) -> bool {
        // Strip "automation." prefix if present
        let id = automation_id.strip_prefix("automation.").unwrap_or(automation_id);

        for auto in &self.automations {
            if auto.id == id {
                tracing::info!("Automation [{}] force-triggered", auto.id);
                self.execute_actions(auto).await;
                return true;
            }
        }
        tracing::warn!("Automation not found: {}", automation_id);
        false
    }

    /// Fire an event and check if any automation triggers on it.
    pub async fn on_event(&self, event_type: &str) -> Vec<String> {
        let mut fired = Vec::new();

        for auto in &self.automations {
            let matches = auto.triggers.iter().any(|t| {
                matches!(t, Trigger::Event { event_type: et } if et == event_type)
            });

            if matches && self.conditions_met(auto) {
                tracing::info!("Automation [{}] triggered by event {}", auto.id, event_type);
                self.execute_actions(auto).await;
                fired.push(auto.id.clone());
            }
        }

        fired
    }

    // ── Trigger Matching ─────────────────────────────────

    fn triggers_match(&self, auto: &Automation, event: &StateChangedEvent) -> bool {
        auto.triggers.iter().any(|trigger| match trigger {
            Trigger::State { entity_id, to, from } => {
                let entity_ids = entity_id.to_vec();
                if !entity_ids.contains(&event.entity_id) {
                    return false;
                }
                // Check "to" filter
                if let Some(to_val) = to {
                    if event.new_state.state != *to_val {
                        return false;
                    }
                }
                // Check "from" filter
                if let Some(from_val) = from {
                    if let Some(old) = &event.old_state {
                        if old.state != *from_val {
                            return false;
                        }
                    } else {
                        return false;
                    }
                }
                true
            }
            // Time, Sun, Event triggers don't match on state_changed
            _ => false,
        })
    }

    // ── Condition Evaluation ─────────────────────────────

    fn conditions_met(&self, auto: &Automation) -> bool {
        if auto.conditions.is_empty() {
            return true;
        }
        // All conditions must be true (implicit AND)
        auto.conditions.iter().all(|cond| self.evaluate_condition(cond))
    }

    fn evaluate_condition(&self, condition: &Condition) -> bool {
        match condition {
            Condition::State { entity_id, state } => {
                match self.app.state_machine.get(entity_id) {
                    Some(current) => current.state == *state,
                    None => false,
                }
            }
            Condition::Or { conditions } => {
                conditions.iter().any(|c| self.evaluate_condition(c))
            }
            Condition::And { conditions } => {
                conditions.iter().all(|c| self.evaluate_condition(c))
            }
        }
    }

    // ── Action Execution ─────────────────────────────────

    async fn execute_actions(&self, auto: &Automation) {
        for action in &auto.actions {
            self.execute_action(action).await;
        }
    }

    async fn execute_action(&self, action: &Action) {
        let parts: Vec<&str> = action.action.splitn(2, '.').collect();
        if parts.len() != 2 {
            tracing::warn!("Invalid action format: {}", action.action);
            return;
        }
        let domain = parts[0];
        let service = parts[1];

        // Extract entity IDs from target
        let entity_ids = action.target.as_ref()
            .and_then(|t| t.entity_id.as_ref())
            .map(|e| e.to_vec())
            .unwrap_or_default();

        // Extract data
        let data = action.data.clone().unwrap_or(serde_json::Value::Object(Default::default()));

        for eid in &entity_ids {
            match (domain, service) {
                ("light", "turn_on") => {
                    let mut attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    if let Some(b) = data.get("brightness") {
                        attrs.insert("brightness".to_string(), b.clone());
                    }
                    if let Some(ct) = data.get("color_temp") {
                        attrs.insert("color_temp".to_string(), ct.clone());
                    }
                    if let Some(rgb) = data.get("rgb_color") {
                        attrs.insert("rgb_color".to_string(), rgb.clone());
                    }
                    self.app.state_machine.set(eid.clone(), "on".to_string(), attrs);
                }
                ("light", "turn_off") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "off".to_string(), attrs);
                }
                ("switch", "turn_on") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "on".to_string(), attrs);
                }
                ("switch", "turn_off") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "off".to_string(), attrs);
                }
                ("lock", "lock") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "locked".to_string(), attrs);
                }
                ("lock", "unlock") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "unlocked".to_string(), attrs);
                }
                ("climate", "set_temperature") => {
                    let mut attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    if let Some(temp) = data.get("temperature") {
                        attrs.insert("temperature".to_string(), temp.clone());
                    }
                    let state_str = self.app.state_machine.get(eid)
                        .map(|s| s.state.clone())
                        .unwrap_or_else(|| "heat".to_string());
                    self.app.state_machine.set(eid.clone(), state_str, attrs);
                }
                ("alarm_control_panel", "arm_home") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "armed_home".to_string(), attrs);
                }
                ("alarm_control_panel", "arm_night") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "armed_night".to_string(), attrs);
                }
                ("alarm_control_panel", "disarm") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "disarmed".to_string(), attrs);
                }
                ("media_player", "turn_on") => {
                    let mut attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    if let Some(source) = data.get("source") {
                        attrs.insert("source".to_string(), source.clone());
                    }
                    self.app.state_machine.set(eid.clone(), "on".to_string(), attrs);
                }
                ("media_player", "turn_off") => {
                    let attrs = self.app.state_machine.get(eid)
                        .map(|s| s.attributes.clone())
                        .unwrap_or_default();
                    self.app.state_machine.set(eid.clone(), "off".to_string(), attrs);
                }
                ("scene", "turn_on") => {
                    if let Some(scenes) = &self.scenes {
                        scenes.turn_on(eid);
                    }
                }
                ("persistent_notification", "create") => {
                    let title = data.get("title").and_then(|v| v.as_str()).unwrap_or("");
                    let message = data.get("message").and_then(|v| v.as_str()).unwrap_or("");
                    tracing::info!("NOTIFICATION: {} — {}", title, message);
                }
                _ => {
                    tracing::warn!("Unhandled action: {}.{}", domain, service);
                }
            }
        }

        // Handle actions with no entity targets (e.g., persistent_notification)
        if entity_ids.is_empty() {
            if domain == "persistent_notification" && service == "create" {
                let title = data.get("title").and_then(|v| v.as_str()).unwrap_or("");
                let message = data.get("message").and_then(|v| v.as_str()).unwrap_or("");
                tracing::info!("NOTIFICATION: {} — {}", title, message);
            }
        }
    }

    /// Get automation IDs (for registering automation entities)
    pub fn automation_ids(&self) -> Vec<String> {
        self.automations.iter().map(|a| a.id.clone()).collect()
    }
}
