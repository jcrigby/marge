use std::sync::atomic::Ordering;
use std::time::Duration;

use chrono::Datelike;
use dashmap::DashMap;
use serde::Deserialize;
use serde_json::Value;
use std::path::Path;
use std::sync::Arc;

use crate::api::AppState;
use crate::scene::SceneEngine;
use crate::services::ServiceRegistry;
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
        event: String,
        #[serde(default)]
        offset: Option<String>,
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
    #[serde(rename = "template")]
    Template {
        value_template: String,
    },
    #[serde(rename = "numeric_state")]
    NumericState {
        entity_id: String,
        #[serde(default)]
        above: Option<f64>,
        #[serde(default)]
        below: Option<f64>,
    },
    #[serde(rename = "time")]
    Time {
        #[serde(default)]
        after: Option<String>,
        #[serde(default)]
        before: Option<String>,
    },
}

/// An action in an automation sequence.
///
/// Service calls have `action` set (e.g., "light.turn_on").
/// Script directives use one of: delay, wait_template, choose, repeat, parallel.
#[derive(Debug, Clone, Deserialize)]
pub struct Action {
    #[serde(default)]
    pub action: Option<String>,
    #[serde(default)]
    pub target: Option<ActionTarget>,
    #[serde(default)]
    pub data: Option<Value>,
    // Script directives (Phase 3 §3.3)
    #[serde(default)]
    pub delay: Option<DelayValue>,
    #[serde(default)]
    pub wait_template: Option<String>,
    #[serde(default)]
    pub timeout: Option<String>,
    #[serde(default)]
    pub choose: Option<Vec<ChooseOption>>,
    #[serde(default)]
    #[serde(rename = "default")]
    pub choose_default: Option<Vec<Action>>,
    #[serde(default)]
    pub repeat: Option<RepeatConfig>,
    #[serde(default)]
    pub variables: Option<serde_json::Map<String, Value>>,
    #[serde(default)]
    pub parallel: Option<Vec<Vec<Action>>>,
}

/// Delay value: "HH:MM:SS" string or numeric seconds.
#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum DelayValue {
    Duration(String),
    Seconds(f64),
}

/// An option branch in a choose action.
#[derive(Debug, Clone, Deserialize)]
pub struct ChooseOption {
    pub conditions: Vec<Condition>,
    pub sequence: Vec<Action>,
}

/// Configuration for a repeat action.
#[derive(Debug, Clone, Deserialize)]
pub struct RepeatConfig {
    #[serde(default)]
    pub count: Option<u32>,
    #[serde(default, rename = "while")]
    pub while_conditions: Option<Vec<Condition>>,
    #[serde(default)]
    pub until: Option<Vec<Condition>>,
    pub sequence: Vec<Action>,
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

// ── Solar Calculator (Phase 3 §3.2) ─────────────────────

/// Calculate sunrise and sunset times using the NOAA solar position algorithm.
///
/// Returns (sunrise, sunset) as "HH:MM:SS" strings in local time.
/// Uses the simplified equation of time and solar declination.
pub fn calculate_sun_times(lat: f64, lon: f64, tz_hours: f64, day_of_year: u32) -> (String, String) {
    let lat_rad = lat.to_radians();

    // Fractional year (gamma) in radians
    let gamma = 2.0 * std::f64::consts::PI * (day_of_year as f64 - 1.0) / 365.0;

    // Equation of time (minutes)
    let eqtime = 229.18
        * (0.000075
            + 0.001868 * gamma.cos()
            - 0.032077 * gamma.sin()
            - 0.014615 * (2.0 * gamma).cos()
            - 0.040849 * (2.0 * gamma).sin());

    // Solar declination (radians)
    let decl = 0.006918 - 0.399912 * gamma.cos() + 0.070257 * gamma.sin()
        - 0.006758 * (2.0 * gamma).cos()
        + 0.000907 * (2.0 * gamma).sin()
        - 0.002697 * (3.0 * gamma).cos()
        + 0.00148 * (3.0 * gamma).sin();

    // Hour angle for sunrise/sunset
    let zenith = 90.833_f64.to_radians();
    let cos_ha = (zenith.cos() / (lat_rad.cos() * decl.cos())) - lat_rad.tan() * decl.tan();

    if cos_ha.abs() > 1.0 {
        // Polar region — no sunrise or sunset
        return ("00:00:00".to_string(), "23:59:59".to_string());
    }

    let ha = cos_ha.acos().to_degrees();

    // Sunrise and sunset in minutes from midnight UTC
    let sunrise_utc = 720.0 - 4.0 * (lon + ha) - eqtime;
    let sunset_utc = 720.0 - 4.0 * (lon - ha) - eqtime;

    // Convert to local time
    let sunrise_local = sunrise_utc + tz_hours * 60.0;
    let sunset_local = sunset_utc + tz_hours * 60.0;

    let to_hms = |minutes: f64| -> String {
        let total = ((minutes % 1440.0) + 1440.0) % 1440.0;
        let h = (total / 60.0).floor() as u32;
        let m = (total % 60.0).floor() as u32;
        let s = ((total * 60.0) % 60.0).round() as u32 % 60;
        format!("{:02}:{:02}:{:02}", h, m, s)
    };

    (to_hms(sunrise_local), to_hms(sunset_local))
}

/// Apply a time offset like "-00:30:00" or "+01:00:00" to an HH:MM:SS time.
/// Returns HH:MM (truncated for matching).
pub fn apply_offset(time: &str, offset: Option<&str>) -> String {
    let base_minutes = parse_hhmm(time);
    let offset_minutes = match offset {
        Some(o) => {
            let negative = o.starts_with('-');
            let cleaned = o.trim_start_matches(['+', '-']);
            let mins = parse_hhmm(cleaned) as i32;
            if negative { -mins } else { mins }
        }
        None => 0,
    };
    let total = ((base_minutes as i32 + offset_minutes) % 1440 + 1440) % 1440;
    let h = total / 60;
    let m = total % 60;
    format!("{:02}:{:02}", h, m)
}

/// Parse "HH:MM:SS" or "HH:MM" to minutes from midnight.
fn parse_hhmm(s: &str) -> u32 {
    let parts: Vec<&str> = s.split(':').collect();
    let h: u32 = parts.first().and_then(|p| p.parse().ok()).unwrap_or(0);
    let m: u32 = parts.get(1).and_then(|p| p.parse().ok()).unwrap_or(0);
    h * 60 + m
}

/// Parse a duration string "HH:MM:SS" or numeric seconds to Duration.
fn parse_duration(s: &str) -> Duration {
    let parts: Vec<&str> = s.split(':').collect();
    match parts.len() {
        3 => {
            let h: u64 = parts[0].parse().unwrap_or(0);
            let m: u64 = parts[1].parse().unwrap_or(0);
            let s: u64 = parts[2].parse().unwrap_or(0);
            Duration::from_secs(h * 3600 + m * 60 + s)
        }
        2 => {
            let m: u64 = parts[0].parse().unwrap_or(0);
            let s: u64 = parts[1].parse().unwrap_or(0);
            Duration::from_secs(m * 60 + s)
        }
        _ => Duration::from_secs(s.parse().unwrap_or(0)),
    }
}

/// Check if time_a is in range [after, before) (HH:MM format).
fn time_in_range(time: &str, after: Option<&str>, before: Option<&str>) -> bool {
    let t = parse_hhmm(time);
    if let Some(a) = after {
        if t < parse_hhmm(a) {
            return false;
        }
    }
    if let Some(b) = before {
        if t >= parse_hhmm(b) {
            return false;
        }
    }
    true
}

// ── Engine ───────────────────────────────────────────────

pub struct AutomationEngine {
    automations: Vec<Automation>,
    app: Arc<AppState>,
    scenes: Option<Arc<SceneEngine>>,
    services: Arc<std::sync::RwLock<ServiceRegistry>>,
    /// Tracks last fired HH:MM for time/sun triggers to prevent duplicate fires.
    last_time_triggers: DashMap<String, String>,
    /// Calculated sunrise/sunset times (HH:MM:SS).
    sun_times: std::sync::RwLock<(String, String)>,
}

impl AutomationEngine {
    pub fn new(
        automations: Vec<Automation>,
        app: Arc<AppState>,
        services: Arc<std::sync::RwLock<ServiceRegistry>>,
    ) -> Self {
        tracing::info!("Loaded {} automations", automations.len());
        for auto in &automations {
            tracing::info!(
                "  [{}] {} — {} trigger(s), {} condition(s), {} action(s)",
                auto.id,
                auto.alias,
                auto.triggers.len(),
                auto.conditions.len(),
                auto.actions.len()
            );
        }

        // Calculate initial sun times for configured location
        let now = chrono::Local::now();
        let day = now.ordinal();
        let tz_offset = now.offset().local_minus_utc() as f64 / 3600.0;
        let (sunrise, sunset) = calculate_sun_times(40.3916, -111.8508, tz_offset, day);
        tracing::info!("Sun times (day {}): sunrise={}, sunset={}", day, sunrise, sunset);

        Self {
            automations,
            app,
            scenes: None,
            services,
            last_time_triggers: DashMap::new(),
            sun_times: std::sync::RwLock::new((sunrise, sunset)),
        }
    }

    pub fn set_scenes(&mut self, scenes: Arc<SceneEngine>) {
        self.scenes = Some(scenes);
    }

    // ── State Change Handler ──────────────────────────────

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

    // ── Time/Sun Trigger Loop (Phase 3 §3.1-3.2) ─────────

    /// Run the time/sun trigger evaluation loop.
    /// Polls every 500ms, comparing sim-time or wall clock against time/sun triggers.
    pub async fn run_time_loop(&self) {
        tokio::time::sleep(Duration::from_secs(1)).await;

        let mut last_day = 0u32;

        loop {
            tokio::time::sleep(Duration::from_millis(500)).await;

            let current_time = self.get_current_time();
            if current_time.is_empty() {
                continue;
            }

            // Recalculate sun times if the day changed
            let now = chrono::Local::now();
            let day = now.ordinal();
            if day != last_day {
                last_day = day;
                let tz_offset = now.offset().local_minus_utc() as f64 / 3600.0;
                let (sunrise, sunset) =
                    calculate_sun_times(40.3916, -111.8508, tz_offset, day);
                *self.sun_times.write().unwrap() = (sunrise, sunset);
            }

            // Extract HH:MM for matching
            let current_hhmm = if current_time.len() >= 5 {
                &current_time[..5]
            } else {
                continue;
            };

            for auto in &self.automations {
                for trigger in &auto.triggers {
                    let trigger_hhmm = match trigger {
                        Trigger::Time { at } => {
                            if at.len() >= 5 {
                                Some(at[..5].to_string())
                            } else {
                                None
                            }
                        }
                        Trigger::Sun { event, offset } => {
                            let (sunrise, sunset) = self.sun_times.read().unwrap().clone();
                            let base = match event.as_str() {
                                "sunrise" => sunrise,
                                "sunset" => sunset,
                                _ => continue,
                            };
                            Some(apply_offset(&base, offset.as_deref()))
                        }
                        _ => None,
                    };

                    if let Some(ref trigger_hh) = trigger_hhmm {
                        if trigger_hh == current_hhmm {
                            let key = format!("{}:{}", auto.id, trigger_hh);

                            // Prevent duplicate firing within the same minute
                            if let Some(last) = self.last_time_triggers.get(&key) {
                                if *last == current_hhmm {
                                    continue;
                                }
                            }

                            if self.conditions_met(auto) {
                                tracing::info!(
                                    "Automation [{}] time-triggered at {}",
                                    auto.id,
                                    current_time
                                );
                                self.execute_actions(auto).await;
                                self.last_time_triggers
                                    .insert(key, current_hhmm.to_string());
                            }
                        }
                    }
                }
            }
        }
    }

    /// Get current time: sim-time if set, otherwise wall clock HH:MM:SS.
    fn get_current_time(&self) -> String {
        let sim_time = self.app.sim_time.lock().unwrap().clone();
        if !sim_time.is_empty() {
            sim_time
        } else {
            chrono::Local::now().format("%H:%M:%S").to_string()
        }
    }

    // ── Trigger Matching ──────────────────────────────────

    fn triggers_match(&self, auto: &Automation, event: &StateChangedEvent) -> bool {
        auto.triggers.iter().any(|trigger| match trigger {
            Trigger::State {
                entity_id,
                to,
                from,
            } => {
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
            // (handled by run_time_loop and on_event respectively)
            _ => false,
        })
    }

    // ── Condition Evaluation ──────────────────────────────

    fn conditions_met(&self, auto: &Automation) -> bool {
        if auto.conditions.is_empty() {
            return true;
        }
        // All conditions must be true (implicit AND)
        auto.conditions
            .iter()
            .all(|cond| self.evaluate_condition(cond))
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
            Condition::Template { value_template } => {
                match crate::template::render_with_state_machine(
                    value_template,
                    &self.app.state_machine,
                ) {
                    Ok(result) => {
                        let t = result.trim();
                        t == "true" || t == "True" || t == "1"
                    }
                    Err(e) => {
                        tracing::warn!("Template condition error: {}", e);
                        false
                    }
                }
            }
            Condition::NumericState {
                entity_id,
                above,
                below,
            } => match self.app.state_machine.get(entity_id) {
                Some(current) => {
                    let val: f64 = match current.state.parse() {
                        Ok(v) => v,
                        Err(_) => return false,
                    };
                    if let Some(a) = above {
                        if val <= *a {
                            return false;
                        }
                    }
                    if let Some(b) = below {
                        if val >= *b {
                            return false;
                        }
                    }
                    true
                }
                None => false,
            },
            Condition::Time { after, before } => {
                let current = self.get_current_time();
                time_in_range(&current, after.as_deref(), before.as_deref())
            }
        }
    }

    // ── Action Execution ──────────────────────────────────

    async fn execute_actions(&self, auto: &Automation) {
        for action in &auto.actions {
            self.execute_action(action).await;
        }
    }

    /// Execute a single action. Uses Box::pin for recursion (choose/repeat/parallel
    /// call back into execute_action).
    fn execute_action<'a>(
        &'a self,
        action: &'a Action,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = ()> + Send + 'a>> {
        Box::pin(async move {
            // Service call: action field is set (e.g., "light.turn_on")
            if let Some(action_str) = &action.action {
                self.execute_service_call(action_str, &action.target, &action.data)
                    .await;
                return;
            }

            // Delay (Phase 3 §3.3)
            if let Some(delay) = &action.delay {
                self.execute_delay(delay).await;
                return;
            }

            // Wait template (Phase 3 §3.3)
            if let Some(template) = &action.wait_template {
                self.execute_wait_template(template, action.timeout.as_deref())
                    .await;
                return;
            }

            // Choose (Phase 3 §3.3)
            if let Some(options) = &action.choose {
                self.execute_choose(options, action.choose_default.as_deref())
                    .await;
                return;
            }

            // Repeat (Phase 3 §3.3)
            if let Some(config) = &action.repeat {
                self.execute_repeat(config).await;
                return;
            }

            // Variables (Phase 3 §3.3) — scoped variables, currently logged
            if action.variables.is_some() {
                tracing::debug!(
                    "Variables action — scoped variable assignment (no-op in engine)"
                );
                return;
            }

            // Parallel (Phase 3 §3.3) — runs sequences sequentially
            if let Some(sequences) = &action.parallel {
                for seq in sequences {
                    for a in seq {
                        self.execute_action(a).await;
                    }
                }
                return;
            }

            tracing::warn!("Unknown action type in automation");
        })
    }

    async fn execute_service_call(
        &self,
        action_str: &str,
        target: &Option<ActionTarget>,
        data: &Option<Value>,
    ) {
        let parts: Vec<&str> = action_str.splitn(2, '.').collect();
        if parts.len() != 2 {
            tracing::warn!("Invalid action format: {}", action_str);
            return;
        }
        let domain = parts[0];
        let service = parts[1];

        let entity_ids = target
            .as_ref()
            .and_then(|t| t.entity_id.as_ref())
            .map(|e| e.to_vec())
            .unwrap_or_default();

        let data = data
            .clone()
            .unwrap_or(Value::Object(Default::default()));

        // Special case: scene.turn_on goes through scene engine
        if domain == "scene" && service == "turn_on" {
            if let Some(scenes) = &self.scenes {
                for eid in &entity_ids {
                    scenes.turn_on(eid);
                }
            }
            return;
        }

        // Dispatch through service registry
        if !entity_ids.is_empty() {
            let registry = self.services.read().unwrap();
            registry.call(domain, service, &entity_ids, &data, &self.app.state_machine);
        }

        // Handle actions with no entity targets (e.g., persistent_notification)
        if entity_ids.is_empty() {
            let registry = self.services.read().unwrap();
            registry.call(
                domain,
                service,
                &["".to_string()],
                &data,
                &self.app.state_machine,
            );
        }
    }

    async fn execute_delay(&self, delay: &DelayValue) {
        let duration = match delay {
            DelayValue::Duration(s) => parse_duration(s),
            DelayValue::Seconds(s) => Duration::from_secs_f64(*s),
        };

        // Scale delay by sim-speed if running in demo mode
        let speed = self.app.sim_speed.load(Ordering::Relaxed);
        let actual = if speed > 1 {
            duration / speed
        } else {
            duration
        };

        tracing::debug!("Delay: {:?} (actual: {:?})", duration, actual);
        tokio::time::sleep(actual).await;
    }

    async fn execute_wait_template(&self, template: &str, timeout: Option<&str>) {
        let timeout_dur = timeout
            .map(|t| parse_duration(t))
            .unwrap_or(Duration::from_secs(300));
        let start = std::time::Instant::now();

        loop {
            if start.elapsed() > timeout_dur {
                tracing::warn!("wait_template timed out: {}", template);
                break;
            }

            match crate::template::render_with_state_machine(template, &self.app.state_machine) {
                Ok(result) => {
                    let t = result.trim();
                    if t == "true" || t == "True" || t == "1" {
                        break;
                    }
                }
                Err(e) => {
                    tracing::warn!("wait_template error: {}", e);
                    break;
                }
            }

            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    }

    async fn execute_choose(&self, options: &[ChooseOption], default: Option<&[Action]>) {
        for option in options {
            if option
                .conditions
                .iter()
                .all(|c| self.evaluate_condition(c))
            {
                for action in &option.sequence {
                    self.execute_action(action).await;
                }
                return;
            }
        }

        // No option matched — run default if provided
        if let Some(default_actions) = default {
            for action in default_actions {
                self.execute_action(action).await;
            }
        }
    }

    async fn execute_repeat(&self, config: &RepeatConfig) {
        const MAX_ITERATIONS: u32 = 1000;

        if let Some(count) = config.count {
            for _ in 0..count.min(MAX_ITERATIONS) {
                for action in &config.sequence {
                    self.execute_action(action).await;
                }
            }
        } else if let Some(while_conds) = &config.while_conditions {
            let mut i = 0;
            while while_conds.iter().all(|c| self.evaluate_condition(c)) && i < MAX_ITERATIONS {
                for action in &config.sequence {
                    self.execute_action(action).await;
                }
                i += 1;
            }
        } else if let Some(until_conds) = &config.until {
            let mut i = 0;
            loop {
                for action in &config.sequence {
                    self.execute_action(action).await;
                }
                i += 1;
                if until_conds.iter().all(|c| self.evaluate_condition(c)) || i >= MAX_ITERATIONS {
                    break;
                }
            }
        }
    }

    /// Get automation IDs (for registering automation entities)
    pub fn automation_ids(&self) -> Vec<String> {
        self.automations.iter().map(|a| a.id.clone()).collect()
    }
}

// ── Tests ────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sun_times_lehi_february() {
        // Lehi, Utah (40.3916°N, 111.8508°W) in February (day ~44)
        // MST = UTC-7
        let (sunrise, sunset) = calculate_sun_times(40.3916, -111.8508, -7.0, 44);

        // Sunrise should be around 7:00-7:30 AM
        let sr_min = parse_hhmm(&sunrise);
        assert!(sr_min >= 420 && sr_min <= 450, "sunrise {} not in 7:00-7:30", sunrise);

        // Sunset should be around 5:40-6:10 PM
        let ss_min = parse_hhmm(&sunset);
        assert!(ss_min >= 1060 && ss_min <= 1090, "sunset {} not in 17:40-18:10", sunset);
    }

    #[test]
    fn test_sun_times_summer_solstice() {
        // Same location, June 21 (day ~172)
        let (sunrise, sunset) = calculate_sun_times(40.3916, -111.8508, -6.0, 172); // MDT = UTC-6

        let sr_min = parse_hhmm(&sunrise);
        assert!(sr_min >= 340 && sr_min <= 380, "sunrise {} not in 5:40-6:20", sunrise);

        let ss_min = parse_hhmm(&sunset);
        assert!(ss_min >= 1260 && ss_min <= 1300, "sunset {} not in 21:00-21:40", sunset);
    }

    #[test]
    fn test_apply_offset() {
        assert_eq!(apply_offset("18:00:00", None), "18:00");
        assert_eq!(apply_offset("18:00:00", Some("-00:30:00")), "17:30");
        assert_eq!(apply_offset("18:00:00", Some("+01:00:00")), "19:00");
        assert_eq!(apply_offset("00:15:00", Some("-00:30:00")), "23:45"); // wrap
    }

    #[test]
    fn test_parse_duration() {
        assert_eq!(parse_duration("00:00:30"), Duration::from_secs(30));
        assert_eq!(parse_duration("01:30:00"), Duration::from_secs(5400));
        assert_eq!(parse_duration("05:00"), Duration::from_secs(300));
        assert_eq!(parse_duration("120"), Duration::from_secs(120));
    }

    #[test]
    fn test_time_in_range() {
        assert!(time_in_range("12:00", Some("08:00"), Some("18:00")));
        assert!(!time_in_range("06:00", Some("08:00"), Some("18:00")));
        assert!(!time_in_range("20:00", Some("08:00"), Some("18:00")));
        assert!(time_in_range("12:00", None, Some("18:00")));
        assert!(time_in_range("12:00", Some("08:00"), None));
    }

    #[test]
    fn test_existing_automations_parse() {
        // Verify the demo automations.yaml still parses with the new types
        let yaml = r#"
- id: test_action
  alias: "Test"
  triggers:
    - trigger: time
      at: "05:30:00"
  actions:
    - action: light.turn_on
      target:
        entity_id: light.bedroom
      data:
        brightness: 51
"#;
        let automations: Vec<Automation> = serde_yaml::from_str(yaml).unwrap();
        assert_eq!(automations.len(), 1);
        assert_eq!(automations[0].actions[0].action.as_deref(), Some("light.turn_on"));
    }

    #[test]
    fn test_script_actions_parse() {
        let yaml = r#"
- id: test_scripts
  alias: "Script Test"
  triggers:
    - trigger: event
      event_type: test
  actions:
    - delay: "00:00:30"
    - action: light.turn_on
      target:
        entity_id: light.bedroom
    - choose:
        - conditions:
            - condition: state
              entity_id: sensor.temp
              state: "hot"
          sequence:
            - action: fan.turn_on
              target:
                entity_id: fan.bedroom
      default:
        - action: fan.turn_off
          target:
            entity_id: fan.bedroom
    - repeat:
        count: 3
        sequence:
          - action: light.toggle
            target:
              entity_id: light.bedroom
"#;
        let automations: Vec<Automation> = serde_yaml::from_str(yaml).unwrap();
        let auto = &automations[0];
        assert_eq!(auto.actions.len(), 4);

        // Delay
        assert!(auto.actions[0].delay.is_some());
        assert!(auto.actions[0].action.is_none());

        // Service call
        assert_eq!(auto.actions[1].action.as_deref(), Some("light.turn_on"));

        // Choose
        assert!(auto.actions[2].choose.is_some());
        let choose = auto.actions[2].choose.as_ref().unwrap();
        assert_eq!(choose.len(), 1);
        assert!(auto.actions[2].choose_default.is_some());

        // Repeat
        assert!(auto.actions[3].repeat.is_some());
        let repeat = auto.actions[3].repeat.as_ref().unwrap();
        assert_eq!(repeat.count, Some(3));
    }

    #[test]
    fn test_template_condition_parse() {
        let yaml = r#"
- id: test_template
  alias: "Template Test"
  triggers:
    - trigger: state
      entity_id: sensor.temp
  conditions:
    - condition: template
      value_template: "{{ states('sensor.temp') | float > 75 }}"
    - condition: numeric_state
      entity_id: sensor.humidity
      above: 30
      below: 70
    - condition: time
      after: "08:00:00"
      before: "22:00:00"
  actions:
    - action: fan.turn_on
      target:
        entity_id: fan.bedroom
"#;
        let automations: Vec<Automation> = serde_yaml::from_str(yaml).unwrap();
        assert_eq!(automations[0].conditions.len(), 3);
    }

    #[test]
    fn test_sun_trigger_with_offset() {
        let yaml = r#"
- id: test_sun
  alias: "Sun Test"
  triggers:
    - trigger: sun
      event: sunset
      offset: "-00:30:00"
  actions:
    - action: light.turn_on
      target:
        entity_id: light.porch
"#;
        let automations: Vec<Automation> = serde_yaml::from_str(yaml).unwrap();
        match &automations[0].triggers[0] {
            Trigger::Sun { event, offset } => {
                assert_eq!(event, "sunset");
                assert_eq!(offset.as_deref(), Some("-00:30:00"));
            }
            _ => panic!("Expected Sun trigger"),
        }
    }
}
