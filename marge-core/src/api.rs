use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

use crate::state::{EntityState, StateMachine};

/// Shared application state
pub struct AppState {
    pub state_machine: StateMachine,
}

/// POST /api/states/{entity_id} request body
#[derive(Debug, Deserialize)]
pub struct SetStateRequest {
    pub state: String,
    #[serde(default)]
    pub attributes: serde_json::Map<String, serde_json::Value>,
}

/// GET /api/ response — HA compatibility
#[derive(Serialize)]
struct ApiStatus {
    message: String,
}

/// GET /api/config response — minimal HA-compatible config
#[derive(Serialize)]
struct ApiConfig {
    location_name: String,
    latitude: f64,
    longitude: f64,
    elevation: i32,
    unit_system: UnitSystem,
    time_zone: String,
    version: String,
    state: String,
}

#[derive(Serialize)]
struct UnitSystem {
    length: String,
    mass: String,
    temperature: String,
    volume: String,
}

/// POST /api/events/{event_type} response
#[derive(Serialize)]
struct EventResponse {
    message: String,
}

/// POST /api/services/{domain}/{service} response
#[derive(Serialize)]
struct ServiceResponse {
    #[serde(skip_serializing_if = "Vec::is_empty")]
    changed_states: Vec<EntityState>,
}

pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        // HA-compatible REST API (SSS §5.1.1)
        .route("/api/", get(api_status))
        .route("/api/config", get(api_config))
        .route("/api/states", get(get_states))
        .route("/api/states/:entity_id", get(get_state))
        .route("/api/states/:entity_id", post(set_state))
        .route("/api/events/:event_type", post(fire_event))
        .route("/api/services/:domain/:service", post(call_service))
        .route("/api/health", get(health))
        .with_state(state)
}

/// GET /api/ — API running check
async fn api_status() -> Json<ApiStatus> {
    Json(ApiStatus {
        message: "API running.".to_string(),
    })
}

/// GET /api/config — system configuration
async fn api_config() -> Json<ApiConfig> {
    Json(ApiConfig {
        location_name: "Marge Demo Home".to_string(),
        latitude: 40.3916,
        longitude: -111.8508,
        elevation: 1387,
        unit_system: UnitSystem {
            length: "mi".to_string(),
            mass: "lb".to_string(),
            temperature: "°F".to_string(),
            volume: "gal".to_string(),
        },
        time_zone: "America/Denver".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        state: "RUNNING".to_string(),
    })
}

/// GET /api/states — return all entity states
async fn get_states(State(app): State<Arc<AppState>>) -> Json<Vec<EntityState>> {
    Json(app.state_machine.get_all())
}

/// GET /api/states/{entity_id} — return single entity state
async fn get_state(
    State(app): State<Arc<AppState>>,
    Path(entity_id): Path<String>,
) -> Result<Json<EntityState>, StatusCode> {
    app.state_machine
        .get(&entity_id)
        .map(Json)
        .ok_or(StatusCode::NOT_FOUND)
}

/// POST /api/states/{entity_id} — set entity state (HA-compatible)
async fn set_state(
    State(app): State<Arc<AppState>>,
    Path(entity_id): Path<String>,
    Json(body): Json<SetStateRequest>,
) -> impl IntoResponse {
    let new_state = app.state_machine.set(entity_id, body.state, body.attributes);
    (StatusCode::OK, Json(new_state))
}

/// POST /api/events/{event_type} — fire an event
async fn fire_event(
    Path(event_type): Path<String>,
) -> Json<EventResponse> {
    // TODO: Wire into event bus when automation engine lands
    tracing::info!(event_type = %event_type, "Event fired");
    Json(EventResponse {
        message: format!("Event {} fired.", event_type),
    })
}

/// POST /api/services/{domain}/{service} — call a service
async fn call_service(
    State(app): State<Arc<AppState>>,
    Path((domain, service)): Path<(String, String)>,
    Json(body): Json<serde_json::Value>,
) -> Json<ServiceResponse> {
    tracing::info!(domain = %domain, service = %service, "Service called");

    let mut changed = Vec::new();

    // Extract entity_id from body (can be string or array)
    let entity_ids: Vec<String> = match body.get("entity_id") {
        Some(serde_json::Value::String(s)) => vec![s.clone()],
        Some(serde_json::Value::Array(arr)) => {
            arr.iter().filter_map(|v| v.as_str().map(String::from)).collect()
        }
        _ => {
            // Check target.entity_id pattern
            match body.get("target").and_then(|t| t.get("entity_id")) {
                Some(serde_json::Value::String(s)) => vec![s.clone()],
                Some(serde_json::Value::Array(arr)) => {
                    arr.iter().filter_map(|v| v.as_str().map(String::from)).collect()
                }
                _ => vec![],
            }
        }
    };

    for eid in entity_ids {
        let result = match (domain.as_str(), service.as_str()) {
            ("light", "turn_on") => {
                let mut attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                if let Some(b) = body.get("brightness") {
                    attrs.insert("brightness".to_string(), b.clone());
                }
                if let Some(ct) = body.get("color_temp") {
                    attrs.insert("color_temp".to_string(), ct.clone());
                }
                Some(app.state_machine.set(eid.clone(), "on".to_string(), attrs))
            }
            ("light", "turn_off") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "off".to_string(), attrs))
            }
            ("light", "toggle") => {
                let current = app.state_machine.get(&eid);
                let new_state_str = match current.as_ref().map(|s| s.state.as_str()) {
                    Some("on") => "off",
                    _ => "on",
                };
                let attrs = current.map(|s| s.attributes.clone()).unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), new_state_str.to_string(), attrs))
            }
            ("switch", "turn_on") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "on".to_string(), attrs))
            }
            ("switch", "turn_off") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "off".to_string(), attrs))
            }
            ("lock", "lock") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "locked".to_string(), attrs))
            }
            ("lock", "unlock") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "unlocked".to_string(), attrs))
            }
            ("climate", "set_temperature") => {
                let mut attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                if let Some(temp) = body.get("temperature") {
                    attrs.insert("temperature".to_string(), temp.clone());
                }
                let state_str = app.state_machine.get(&eid)
                    .map(|s| s.state.clone())
                    .unwrap_or_else(|| "heat".to_string());
                Some(app.state_machine.set(eid.clone(), state_str, attrs))
            }
            ("climate", "set_hvac_mode") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                let mode = body.get("hvac_mode")
                    .and_then(|v| v.as_str())
                    .unwrap_or("off")
                    .to_string();
                Some(app.state_machine.set(eid.clone(), mode, attrs))
            }
            ("alarm_control_panel", "arm_home") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "armed_home".to_string(), attrs))
            }
            ("alarm_control_panel", "arm_away") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "armed_away".to_string(), attrs))
            }
            ("alarm_control_panel", "arm_night") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "armed_night".to_string(), attrs))
            }
            ("alarm_control_panel", "disarm") => {
                let attrs = app.state_machine.get(&eid)
                    .map(|s| s.attributes.clone())
                    .unwrap_or_default();
                Some(app.state_machine.set(eid.clone(), "disarmed".to_string(), attrs))
            }
            ("persistent_notification", "create") => {
                tracing::info!("Notification: {}", body.get("message").and_then(|v| v.as_str()).unwrap_or(""));
                None
            }
            _ => {
                tracing::warn!(domain = %domain, service = %service, "Unknown service");
                None
            }
        };

        if let Some(state) = result {
            changed.push(state);
        }
    }

    Json(ServiceResponse {
        changed_states: changed,
    })
}

/// GET /api/health — health check with metrics
async fn health(State(app): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let pid = std::process::id();
    let rss_kb = read_rss_kb(pid).unwrap_or(0);

    Json(serde_json::json!({
        "status": "ok",
        "version": env!("CARGO_PKG_VERSION"),
        "entity_count": app.state_machine.len(),
        "memory_rss_kb": rss_kb,
        "uptime_seconds": 0, // TODO: track actual uptime
    }))
}

/// Read RSS from /proc/self/status on Linux
fn read_rss_kb(pid: u32) -> Option<u64> {
    let status = std::fs::read_to_string(format!("/proc/{}/status", pid)).ok()?;
    for line in status.lines() {
        if line.starts_with("VmRSS:") {
            let parts: Vec<&str> = line.split_whitespace().collect();
            return parts.get(1)?.parse().ok();
        }
    }
    None
}
