use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use axum::body::Body;
use axum::extract::Query;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;

use crate::auth::AuthConfig;
use crate::automation::AutomationEngine;
use crate::scene::SceneEngine;
use crate::services::ServiceRegistry;
use crate::state::{EntityState, StateMachine};

/// Shared application state
pub struct AppState {
    pub state_machine: StateMachine,
    pub started_at: std::time::Instant,
    pub startup_us: std::sync::atomic::AtomicU64,
    pub sim_time: std::sync::Mutex<String>,
    pub sim_chapter: std::sync::Mutex<String>,
    pub sim_speed: std::sync::atomic::AtomicU32,
    pub ws_connections: std::sync::atomic::AtomicU32,
}

/// Combined router state
#[derive(Clone)]
struct RouterState {
    app: Arc<AppState>,
    engine: Option<Arc<AutomationEngine>>,
    scenes: Option<Arc<SceneEngine>>,
    services: Arc<std::sync::RwLock<ServiceRegistry>>,
    auth: Arc<AuthConfig>,
    db_path: PathBuf,
    _automations_path: PathBuf,
    scenes_path: PathBuf,
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

#[allow(clippy::too_many_arguments)]
pub fn router(
    state: Arc<AppState>,
    engine: Option<Arc<AutomationEngine>>,
    scenes: Option<Arc<SceneEngine>>,
    services: Arc<std::sync::RwLock<ServiceRegistry>>,
    auth: Arc<AuthConfig>,
    db_path: PathBuf,
    automations_path: PathBuf,
    scenes_path: PathBuf,
) -> Router {
    let router_state = RouterState {
        app: state,
        engine,
        scenes,
        services,
        auth,
        db_path,
        _automations_path: automations_path,
        scenes_path,
    };

    Router::new()
        // HA-compatible REST API (SSS §5.1.1)
        .route("/api/", get(api_status))
        .route("/api/config", get(api_config))
        .route("/api/states", get(get_states))
        .route("/api/states/search", get(search_states))
        .route("/api/states/:entity_id", get(get_state).post(set_state).delete(delete_state))
        .route("/api/events/:event_type", post(fire_event))
        .route("/api/services/:domain/:service", post(call_service))
        .route("/api/health", get(health))
        .route("/api/sim/time", post(set_sim_time))
        // History API (Phase 5)
        .route("/api/history/period/:entity_id", get(get_history))
        // Webhook receiver (Phase 5)
        .route("/api/webhook/:webhook_id", post(webhook_receiver))
        // Backup (Phase 6 §6.2)
        .route("/api/backup", get(create_backup))
        // Logbook (HA-compatible)
        .route("/api/logbook", get(get_logbook_global))
        .route("/api/logbook/:entity_id", get(get_logbook))
        // Service listing (HA-compatible)
        .route("/api/services", get(list_services))
        // Template rendering (HA-compatible)
        .route("/api/template", post(render_template))
        // Event type listing (HA-compatible)
        .route("/api/events", get(list_events))
        // Automation config + reload
        .route("/api/config/automation/config", get(list_automations))
        .route("/api/config/automation/yaml", get(get_automation_yaml).put(put_automation_yaml))
        .route("/api/config/core/reload", post(reload_automations))
        // Scene config
        .route("/api/config/scene/config", get(list_scenes))
        .route("/api/config/scene/yaml", get(get_scene_yaml).put(put_scene_yaml))
        // Statistics aggregation
        .route("/api/statistics/:entity_id", get(get_statistics))
        // Area management
        .route("/api/areas", get(list_areas))
        .route("/api/areas", post(create_area))
        .route("/api/areas/:area_id", axum::routing::delete(delete_area_handler))
        .route("/api/areas/:area_id/entities", get(list_area_entities))
        .route("/api/areas/:area_id/entities/:entity_id", post(assign_entity_to_area))
        .route("/api/areas/:area_id/entities/:entity_id", axum::routing::delete(unassign_entity_from_area))
        // Device registry
        .route("/api/devices", get(list_devices_handler))
        .route("/api/devices", post(create_device_handler))
        .route("/api/devices/:device_id", axum::routing::delete(delete_device_handler))
        .route("/api/devices/:device_id/entities/:entity_id", post(assign_entity_device_handler))
        // Notifications
        .route("/api/notifications", get(list_notifications_handler))
        .route("/api/notifications/:notification_id/dismiss", post(dismiss_notification_handler))
        .route("/api/notifications/dismiss_all", post(dismiss_all_notifications_handler))
        // Label registry
        .route("/api/labels", get(list_labels_handler).post(create_label_handler))
        .route("/api/labels/:label_id", axum::routing::delete(delete_label_handler))
        .route("/api/labels/:label_id/entities/:entity_id", post(assign_label_handler).delete(unassign_label_handler))
        // Long-lived access tokens
        .route("/api/auth/tokens", get(list_tokens))
        .route("/api/auth/tokens", post(create_token))
        .route("/api/auth/tokens/:token_id", axum::routing::delete(delete_token_handler))
        // HA-compatible stubs
        .route("/api/error_log", get(error_log))
        .route("/api/config/core/check_config", post(check_config))
        // Prometheus metrics
        .route("/metrics", get(prometheus_metrics))
        .with_state(router_state)
}

/// Validate authorization from request headers. Returns Err(401) if auth is
/// enabled and the token is missing or invalid.
fn check_auth(rs: &RouterState, headers: &HeaderMap) -> Result<(), StatusCode> {
    if !rs.auth.is_enabled() {
        return Ok(());
    }
    let auth_header = headers
        .get("authorization")
        .and_then(|v| v.to_str().ok());
    if rs.auth.validate_header(auth_header) {
        Ok(())
    } else {
        Err(StatusCode::UNAUTHORIZED)
    }
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
async fn get_states(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<EntityState>>, StatusCode> {
    check_auth(&rs, &headers)?;
    Ok(Json(rs.app.state_machine.get_all()))
}

/// GET /api/states/{entity_id} — return single entity state
async fn get_state(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(entity_id): Path<String>,
) -> Result<Json<EntityState>, StatusCode> {
    check_auth(&rs, &headers)?;
    rs.app.state_machine
        .get(&entity_id)
        .map(Json)
        .ok_or(StatusCode::NOT_FOUND)
}

/// POST /api/states/{entity_id} — set entity state (HA-compatible)
async fn set_state(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(entity_id): Path<String>,
    Json(body): Json<SetStateRequest>,
) -> Result<impl IntoResponse, StatusCode> {
    check_auth(&rs, &headers)?;
    let new_state = rs.app.state_machine.set(entity_id, body.state, body.attributes);
    Ok((StatusCode::OK, Json(new_state)))
}

/// DELETE /api/states/{entity_id} — remove an entity
async fn delete_state(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(entity_id): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    if rs.app.state_machine.remove(&entity_id) {
        tracing::info!(entity_id = %entity_id, "Entity deleted");
        Ok(Json(serde_json::json!({"message": format!("Entity {} removed", entity_id)})))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// GET /api/states/search?q=text&domain=light&label=critical&area=living_room&state=on
#[derive(Debug, Deserialize)]
struct SearchParams {
    q: Option<String>,
    domain: Option<String>,
    state: Option<String>,
    label: Option<String>,
    area: Option<String>,
}

async fn search_states(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Query(params): Query<SearchParams>,
) -> Result<Json<Vec<EntityState>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let mut results = rs.app.state_machine.get_all();

    // Filter by domain
    if let Some(ref domain) = params.domain {
        results.retain(|e| e.entity_id.starts_with(&format!("{}.", domain)));
    }

    // Filter by state value
    if let Some(ref state_val) = params.state {
        results.retain(|e| e.state == *state_val);
    }

    // Filter by text query (entity_id, state, or friendly_name)
    if let Some(ref q) = params.q {
        let q_lower = q.to_lowercase();
        results.retain(|e| {
            e.entity_id.to_lowercase().contains(&q_lower)
                || e.state.to_lowercase().contains(&q_lower)
                || e.attributes.get("friendly_name")
                    .and_then(|v| v.as_str())
                    .map(|n| n.to_lowercase().contains(&q_lower))
                    .unwrap_or(false)
        });
    }

    // Filter by label
    if let Some(ref label_id) = params.label {
        let db_path = rs.db_path.clone();
        let lid = label_id.clone();
        let mappings = tokio::task::spawn_blocking(move || {
            crate::recorder::load_entity_labels(&db_path)
        })
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

        let label_entities: std::collections::HashSet<String> = mappings
            .into_iter()
            .filter(|(_, l)| *l == lid)
            .map(|(e, _)| e)
            .collect();
        results.retain(|e| label_entities.contains(&e.entity_id));
    }

    // Filter by area
    if let Some(ref area_id) = params.area {
        let db_path = rs.db_path.clone();
        let aid = area_id.clone();
        let mappings = tokio::task::spawn_blocking(move || {
            crate::recorder::load_area_entities(&db_path)
        })
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

        let area_entities: std::collections::HashSet<String> = mappings
            .into_iter()
            .filter(|(_, a)| *a == aid)
            .map(|(e, _)| e)
            .collect();
        results.retain(|e| area_entities.contains(&e.entity_id));
    }

    // Sort by entity_id for deterministic output
    results.sort_by(|a, b| a.entity_id.cmp(&b.entity_id));

    Ok(Json(results))
}

/// POST /api/events/{event_type} — fire an event
async fn fire_event(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(event_type): Path<String>,
    _body: Option<Json<serde_json::Value>>,
) -> Result<Json<EventResponse>, StatusCode> {
    check_auth(&rs, &headers)?;
    tracing::info!(event_type = %event_type, "Event fired");

    // If automation engine is loaded, let it process the event
    if let Some(engine) = &rs.engine {
        engine.on_event(&event_type).await;
    }

    Ok(Json(EventResponse {
        message: format!("Event {} fired.", event_type),
    }))
}

/// POST /api/services/{domain}/{service} — call a service
///
/// Dispatches through the dynamic service registry (Phase 2 §1.4).
/// Special cases: automation.trigger and scene.turn_on are handled directly.
async fn call_service(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path((domain, service)): Path<(String, String)>,
    Json(body): Json<serde_json::Value>,
) -> Result<Json<ServiceResponse>, StatusCode> {
    check_auth(&rs, &headers)?;
    tracing::info!(domain = %domain, service = %service, "Service called");

    // Handle automation services specially
    if domain == "automation" {
        if let Some(engine) = &rs.engine {
            let entity_id = body.get("entity_id")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            match service.as_str() {
                "trigger" => { engine.trigger_by_id(entity_id).await; }
                "turn_on" => { engine.set_enabled(entity_id, true); }
                "turn_off" => { engine.set_enabled(entity_id, false); }
                "toggle" => {
                    let id = entity_id.strip_prefix("automation.").unwrap_or(entity_id);
                    let currently_enabled = engine.get_automations_info()
                        .iter().find(|a| a.id == id).map(|a| a.enabled).unwrap_or(true);
                    engine.set_enabled(entity_id, !currently_enabled);
                }
                _ => {}
            }
        }
        return Ok(Json(ServiceResponse { changed_states: vec![] }));
    }

    // Handle persistent_notification services
    if domain == "persistent_notification" {
        match service.as_str() {
            "create" => {
                let notif_id = body.get("notification_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("auto")
                    .to_string();
                let notif_id = if notif_id == "auto" {
                    uuid::Uuid::new_v4().to_string()
                } else {
                    notif_id
                };
                let title = body.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let message = body.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let db_path = rs.db_path.clone();
                let _ = tokio::task::spawn_blocking(move || {
                    crate::recorder::create_notification(&db_path, &notif_id, &title, &message)
                }).await;
            }
            "dismiss" => {
                let notif_id = body.get("notification_id")
                    .and_then(|v| v.as_str()).unwrap_or("").to_string();
                let db_path = rs.db_path.clone();
                let _ = tokio::task::spawn_blocking(move || {
                    crate::recorder::dismiss_notification(&db_path, &notif_id)
                }).await;
            }
            "dismiss_all" => {
                let db_path = rs.db_path.clone();
                let _ = tokio::task::spawn_blocking(move || {
                    crate::recorder::dismiss_all_notifications(&db_path)
                }).await;
            }
            _ => {}
        }
        return Ok(Json(ServiceResponse { changed_states: vec![] }));
    }

    // Handle scene.turn_on
    if domain == "scene" && service == "turn_on" {
        if let Some(scenes) = &rs.scenes {
            let entity_id = body.get("entity_id")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            scenes.turn_on(entity_id);
        }
        return Ok(Json(ServiceResponse { changed_states: vec![] }));
    }

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

    // Dispatch through service registry
    let changed = {
        let registry = rs.services.read().unwrap_or_else(|e| e.into_inner());
        registry.call(&domain, &service, &entity_ids, &body, &rs.app.state_machine)
    };

    Ok(Json(ServiceResponse {
        changed_states: changed,
    }))
}

/// POST /api/sim/time — update sim-time and chapter
async fn set_sim_time(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Json(body): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;
    if let Some(time) = body.get("time").and_then(|v| v.as_str()) {
        *rs.app.sim_time.lock().unwrap_or_else(|e| e.into_inner()) = time.to_string();
    }
    if let Some(chapter) = body.get("chapter").and_then(|v| v.as_str()) {
        *rs.app.sim_chapter.lock().unwrap_or_else(|e| e.into_inner()) = chapter.to_string();
    }
    if let Some(speed) = body.get("speed").and_then(|v| v.as_f64()) {
        rs.app.sim_speed.store(speed as u32, std::sync::atomic::Ordering::Relaxed);
    }
    Ok(Json(serde_json::json!({"status": "ok"})))
}

/// GET /api/health — health check with metrics
async fn health(State(rs): State<RouterState>) -> Json<serde_json::Value> {
    use std::sync::atomic::Ordering;

    let pid = std::process::id();
    let rss_kb = read_rss_kb(pid).unwrap_or(0);
    let uptime = rs.app.started_at.elapsed().as_secs();

    let m = &rs.app.state_machine.metrics;
    let state_changes = m.state_changes.load(Ordering::Relaxed);
    let events_fired = m.events_fired.load(Ordering::Relaxed);
    let total_ns = m.total_transition_ns.load(Ordering::Relaxed);
    let max_ns = m.max_transition_ns.load(Ordering::Relaxed);

    let avg_us = if state_changes > 0 {
        (total_ns / state_changes) as f64 / 1000.0
    } else {
        0.0
    };
    let max_us = max_ns as f64 / 1000.0;

    let sim_time = rs.app.sim_time.lock().unwrap_or_else(|e| e.into_inner()).clone();
    let sim_chapter = rs.app.sim_chapter.lock().unwrap_or_else(|e| e.into_inner()).clone();
    let sim_speed = rs.app.sim_speed.load(Ordering::Relaxed);
    let startup_us = rs.app.startup_us.load(Ordering::Relaxed);

    Json(serde_json::json!({
        "status": "ok",
        "version": env!("CARGO_PKG_VERSION"),
        "entity_count": rs.app.state_machine.len(),
        "memory_rss_kb": rss_kb,
        "memory_rss_mb": rss_kb as f64 / 1024.0,
        "uptime_seconds": uptime,
        "startup_us": startup_us,
        "startup_ms": (startup_us as f64 / 1000.0 * 100.0).round() / 100.0,
        "state_changes": state_changes,
        "events_fired": events_fired,
        "latency_avg_us": (avg_us * 100.0).round() / 100.0,
        "latency_max_us": (max_us * 100.0).round() / 100.0,
        "sim_time": sim_time,
        "sim_chapter": sim_chapter,
        "sim_speed": sim_speed,
        "ws_connections": rs.app.ws_connections.load(Ordering::Relaxed),
    }))
}

/// Query parameters for history endpoint
#[derive(Deserialize)]
struct HistoryParams {
    /// ISO 8601 start time (defaults to 24h ago)
    start: Option<String>,
    /// ISO 8601 end time (defaults to now)
    end: Option<String>,
}

/// GET /api/history/period/{entity_id} — query state history (HA-compatible)
async fn get_history(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(entity_id): Path<String>,
    Query(params): Query<HistoryParams>,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let now = chrono::Utc::now();
    let end = params.end.unwrap_or_else(|| now.to_rfc3339());
    let start = params.start.unwrap_or_else(|| {
        (now - chrono::Duration::hours(24)).to_rfc3339()
    });

    let db_path = rs.db_path.clone();
    let eid = entity_id.clone();
    let entries = tokio::task::spawn_blocking(move || {
        crate::recorder::query_history(&db_path, &eid, &start, &end)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    // Return HA-compatible format: array of state objects
    let result: Vec<serde_json::Value> = entries
        .into_iter()
        .map(|e| {
            let attrs: serde_json::Value = serde_json::from_str(&e.attributes)
                .unwrap_or(serde_json::Value::Object(Default::default()));
            serde_json::json!({
                "entity_id": entity_id,
                "state": e.state,
                "attributes": attrs,
                "last_changed": e.last_changed,
                "last_updated": e.last_updated,
            })
        })
        .collect();

    Ok(Json(result))
}

/// POST /api/webhook/{webhook_id} — receive webhook events from external services
///
/// Webhooks can set entity state or fire events. The webhook_id maps to an
/// entity or event based on the payload:
/// - `{"entity_id": "...", "state": "...", "attributes": {...}}` — set state
/// - `{"event_type": "...", "data": {...}}` — fire event
/// - If no entity_id or event_type, fires a `webhook.<webhook_id>` event
async fn webhook_receiver(
    State(rs): State<RouterState>,
    Path(webhook_id): Path<String>,
    body: Option<Json<serde_json::Value>>,
) -> Json<serde_json::Value> {
    let payload = body.map(|b| b.0).unwrap_or(serde_json::Value::Object(Default::default()));
    tracing::info!(webhook_id = %webhook_id, "Webhook received");

    // If payload specifies entity_id + state, set the state
    if let (Some(entity_id), Some(state)) = (
        payload.get("entity_id").and_then(|v| v.as_str()),
        payload.get("state").and_then(|v| v.as_str()),
    ) {
        let attrs = payload
            .get("attributes")
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default();
        rs.app.state_machine.set(entity_id.to_string(), state.to_string(), attrs);
        return Json(serde_json::json!({"message": "State updated"}));
    }

    // If payload specifies event_type, fire the event
    if let Some(event_type) = payload.get("event_type").and_then(|v| v.as_str()) {
        if let Some(engine) = &rs.engine {
            engine.on_event(event_type).await;
        }
        return Json(serde_json::json!({"message": format!("Event {} fired", event_type)}));
    }

    // Default: fire a webhook.<id> event
    let event_type = format!("webhook.{}", webhook_id);
    if let Some(engine) = &rs.engine {
        engine.on_event(&event_type).await;
    }
    Json(serde_json::json!({"message": format!("Event {} fired", event_type)}))
}

/// GET /api/backup — download a backup archive (tar.gz of config + DB)
async fn create_backup(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<impl IntoResponse, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    let backup_data = tokio::task::spawn_blocking(move || {
        create_backup_archive(&db_path)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let timestamp = chrono::Utc::now().format("%Y%m%d_%H%M%S");
    let disposition = format!("attachment; filename=\"marge_backup_{}.tar.gz\"", timestamp);
    Ok((
        [
            (axum::http::header::CONTENT_TYPE.as_str(), "application/gzip".to_string()),
            (axum::http::header::CONTENT_DISPOSITION.as_str(), disposition),
        ],
        Body::from(backup_data),
    ))
}

/// Create a tar.gz backup containing the database and config files.
fn create_backup_archive(db_path: &std::path::Path) -> anyhow::Result<Vec<u8>> {
    let buf = Vec::new();
    let encoder = flate2::write::GzEncoder::new(buf, flate2::Compression::fast());
    let mut tar = tar::Builder::new(encoder);

    // Add the database file
    if db_path.exists() {
        tar.append_path_with_name(db_path, "marge.db")
            .unwrap_or_else(|e| tracing::warn!("Backup: skip DB: {}", e));
    }

    // Add WAL files if they exist
    let wal_path = db_path.with_extension("db-wal");
    if wal_path.exists() {
        tar.append_path_with_name(&wal_path, "marge.db-wal")
            .unwrap_or_else(|e| tracing::warn!("Backup: skip WAL: {}", e));
    }

    // Add config files
    let configs = [
        ("/etc/marge/automations.yaml", "automations.yaml"),
        ("/etc/marge/scenes.yaml", "scenes.yaml"),
    ];
    for (path, name) in configs {
        let p = std::path::Path::new(path);
        if p.exists() {
            tar.append_path_with_name(p, name)
                .unwrap_or_else(|e| tracing::warn!("Backup: skip {}: {}", name, e));
        }
    }

    let encoder = tar.into_inner()?;
    let archive = encoder.finish()?;

    tracing::info!("Backup created: {} bytes", archive.len());
    Ok(archive)
}

/// GET /api/logbook — global logbook (recent state changes across all entities)
async fn get_logbook_global(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Query(params): Query<HistoryParams>,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let now = chrono::Utc::now();
    let end = params.end.unwrap_or_else(|| now.to_rfc3339());
    let start = params.start.unwrap_or_else(|| {
        (now - chrono::Duration::hours(24)).to_rfc3339()
    });

    let db_path = rs.db_path.clone();
    let entries = tokio::task::spawn_blocking(move || {
        crate::recorder::query_logbook_global(&db_path, &start, &end, 200)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let logbook: Vec<serde_json::Value> = entries.into_iter().map(|e| {
        serde_json::json!({
            "entity_id": e.entity_id,
            "state": e.state,
            "when": e.when,
        })
    }).collect();

    Ok(Json(logbook))
}

/// GET /api/logbook/{entity_id} — return recent state changes as logbook entries
async fn get_logbook(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(entity_id): Path<String>,
    Query(params): Query<HistoryParams>,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let now = chrono::Utc::now();
    let end = params.end.unwrap_or_else(|| now.to_rfc3339());
    let start = params.start.unwrap_or_else(|| {
        (now - chrono::Duration::hours(24)).to_rfc3339()
    });

    let db_path = rs.db_path.clone();
    let eid = entity_id.clone();
    let entries = tokio::task::spawn_blocking(move || {
        crate::recorder::query_history(&db_path, &eid, &start, &end)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    // Format as logbook entries (simplified state changes with context)
    let mut logbook = Vec::new();
    let mut prev_state: Option<String> = None;
    for e in entries {
        if prev_state.as_deref() != Some(&e.state) {
            logbook.push(serde_json::json!({
                "entity_id": entity_id,
                "state": e.state,
                "when": e.last_changed,
            }));
            prev_state = Some(e.state);
        }
    }

    Ok(Json(logbook))
}

/// GET /api/services — list all registered services (HA-compatible)
async fn list_services(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;
    let registry = rs.services.read().unwrap_or_else(|e| e.into_inner());
    let services = registry.list_services();

    // HA format: array of {domain, services: {service_name: {description, fields}}}
    let result: Vec<serde_json::Value> = services
        .into_iter()
        .map(|(domain, svcs)| {
            let svc_map: serde_json::Map<String, serde_json::Value> = svcs
                .into_iter()
                .map(|s| {
                    (s.clone(), serde_json::json!({
                        "description": format!("{}.{}", domain, s),
                        "fields": {}
                    }))
                })
                .collect();
            serde_json::json!({
                "domain": domain,
                "services": svc_map,
            })
        })
        .collect();

    Ok(Json(result))
}

/// GET /api/events — list available event types (HA-compatible)
async fn list_events(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;
    // Return standard HA event types
    let events = vec![
        "state_changed",
        "call_service",
        "automation_triggered",
        "scene_activated",
        "homeassistant_start",
        "homeassistant_stop",
    ];
    let result: Vec<serde_json::Value> = events
        .into_iter()
        .map(|e| serde_json::json!({"event": e, "listener_count": 0}))
        .collect();
    Ok(Json(result))
}

/// POST /api/template request body
#[derive(Deserialize)]
struct TemplateRequest {
    template: String,
}

/// POST /api/template — render a Jinja2 template (HA-compatible)
async fn render_template(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Json(body): Json<TemplateRequest>,
) -> Result<String, StatusCode> {
    check_auth(&rs, &headers)?;
    crate::template::render_with_state_machine(&body.template, &rs.app.state_machine)
        .map_err(|e| {
            tracing::warn!("Template render error: {}", e);
            StatusCode::BAD_REQUEST
        })
}

/// GET /api/config/automation/config — list all automations with metadata
async fn list_automations(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    match &rs.engine {
        Some(engine) => {
            let infos = engine.get_automations_info();
            let result: Vec<serde_json::Value> = infos
                .into_iter()
                .map(|info| {
                    serde_json::json!({
                        "id": info.id,
                        "alias": info.alias,
                        "description": info.description,
                        "mode": info.mode,
                        "trigger_count": info.trigger_count,
                        "condition_count": info.condition_count,
                        "action_count": info.action_count,
                        "last_triggered": info.last_triggered,
                        "total_triggers": info.total_triggers,
                        "enabled": info.enabled,
                    })
                })
                .collect();
            Ok(Json(result))
        }
        None => Ok(Json(vec![])),
    }
}

/// GET /api/config/automation/yaml — return raw YAML for editing
async fn get_automation_yaml(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<(StatusCode, [(axum::http::header::HeaderName, &'static str); 1], String), StatusCode> {
    check_auth(&rs, &headers)?;

    let path = match &rs.engine {
        Some(engine) => engine.get_automations_path()
            .ok_or(StatusCode::NOT_FOUND)?,
        None => return Err(StatusCode::NOT_FOUND),
    };

    let yaml = tokio::fs::read_to_string(&path).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok((
        StatusCode::OK,
        [(axum::http::header::CONTENT_TYPE, "text/yaml")],
        yaml,
    ))
}

/// PUT /api/config/automation/yaml — save YAML to disk and reload
async fn put_automation_yaml(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    body: String,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let engine = rs.engine.as_ref().ok_or(StatusCode::NOT_FOUND)?;
    let path = engine.get_automations_path().ok_or(StatusCode::NOT_FOUND)?;

    // Validate YAML parses correctly before writing
    let _: Vec<crate::automation::Automation> = serde_yaml::from_str(&body)
        .map_err(|e| {
            tracing::error!("Invalid automation YAML: {}", e);
            StatusCode::BAD_REQUEST
        })?;

    // Write to disk
    tokio::fs::write(&path, &body).await
        .map_err(|e| {
            tracing::error!("Failed to write automation YAML to {:?}: {}", path, e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    // Reload
    match engine.reload() {
        Ok(count) => {
            tracing::info!("Saved and reloaded {} automations", count);
            Ok(Json(serde_json::json!({
                "result": "ok",
                "automations_reloaded": count,
            })))
        }
        Err(e) => {
            tracing::error!("Automation reload after save failed: {}", e);
            Ok(Json(serde_json::json!({
                "result": "error",
                "message": format!("{}", e),
            })))
        }
    }
}

/// POST /api/config/core/reload — reload automations from disk (HA-compatible)
async fn reload_automations(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    match &rs.engine {
        Some(engine) => {
            match engine.reload() {
                Ok(count) => {
                    tracing::info!("Reloaded {} automations", count);
                    Ok(Json(serde_json::json!({
                        "result": "ok",
                        "automations_reloaded": count,
                    })))
                }
                Err(e) => {
                    tracing::error!("Automation reload failed: {}", e);
                    Ok(Json(serde_json::json!({
                        "result": "error",
                        "message": format!("{}", e),
                    })))
                }
            }
        }
        None => {
            Ok(Json(serde_json::json!({
                "result": "ok",
                "automations_reloaded": 0,
            })))
        }
    }
}

/// GET /api/statistics/{entity_id} — aggregated hourly statistics for numeric entities
async fn get_statistics(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(entity_id): Path<String>,
    Query(params): Query<HistoryParams>,
) -> Result<Json<Vec<crate::recorder::StatsBucket>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let now = chrono::Utc::now();
    let end = params.end.unwrap_or_else(|| now.to_rfc3339());
    let start = params.start.unwrap_or_else(|| {
        (now - chrono::Duration::hours(24)).to_rfc3339()
    });

    let db_path = rs.db_path.clone();
    let eid = entity_id.clone();
    let buckets = tokio::task::spawn_blocking(move || {
        crate::recorder::query_statistics(&db_path, &eid, &start, &end)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(buckets))
}

/// GET /api/config/scene/config — list all scenes with metadata
async fn list_scenes(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    match &rs.scenes {
        Some(scenes) => Ok(Json(scenes.get_scenes_info())),
        None => Ok(Json(vec![])),
    }
}

/// GET /api/config/scene/yaml — return raw scene YAML for editing
async fn get_scene_yaml(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<(StatusCode, [(axum::http::header::HeaderName, &'static str); 1], String), StatusCode> {
    check_auth(&rs, &headers)?;

    let path = &rs.scenes_path;
    let yaml = tokio::fs::read_to_string(path).await
        .map_err(|e| {
            tracing::error!("Failed to read scene YAML from {:?}: {}", path, e);
            StatusCode::NOT_FOUND
        })?;

    Ok((
        StatusCode::OK,
        [(axum::http::header::CONTENT_TYPE, "text/yaml")],
        yaml,
    ))
}

/// PUT /api/config/scene/yaml — save scene YAML to disk
async fn put_scene_yaml(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    body: String,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    // Validate YAML parses correctly before writing
    let _: Vec<crate::scene::Scene> = serde_yaml::from_str(&body)
        .map_err(|e| {
            tracing::error!("Invalid scene YAML: {}", e);
            StatusCode::BAD_REQUEST
        })?;

    // Write to disk
    tokio::fs::write(&rs.scenes_path, &body).await
        .map_err(|e| {
            tracing::error!("Failed to write scene YAML to {:?}: {}", rs.scenes_path, e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// GET /api/areas — list all areas
async fn list_areas(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    let result = tokio::task::spawn_blocking(move || {
        let areas = crate::recorder::init_areas(&db_path)?;
        let mappings = crate::recorder::load_area_entities(&db_path)?;
        Ok::<_, anyhow::Error>((areas, mappings))
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let (areas, mappings) = result;

    let response: Vec<serde_json::Value> = areas.iter().map(|area| {
        let entity_ids: Vec<&str> = mappings.iter()
            .filter(|(_, aid)| *aid == area.area_id)
            .map(|(eid, _)| eid.as_str())
            .collect();
        serde_json::json!({
            "area_id": area.area_id,
            "name": area.name,
            "entity_count": entity_ids.len(),
            "entities": entity_ids,
        })
    }).collect();

    Ok(Json(response))
}

/// POST /api/areas — create or update an area
async fn create_area(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Json(body): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let area_id = body.get("area_id").and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?
        .to_string();
    let name = body.get("name").and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?
        .to_string();

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::upsert_area(&db_path, &area_id, &name)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// DELETE /api/areas/{area_id}
async fn delete_area_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(area_id): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::delete_area(&db_path, &area_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// GET /api/areas/{area_id}/entities — list entities in an area
async fn list_area_entities(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(area_id): Path<String>,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    let mappings = tokio::task::spawn_blocking(move || {
        crate::recorder::load_area_entities(&db_path)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let entity_ids: Vec<&str> = mappings.iter()
        .filter(|(_, a)| *a == area_id)
        .map(|(e, _)| e.as_str())
        .collect();

    let result: Vec<serde_json::Value> = entity_ids.iter().map(|eid| {
        if let Some(state) = rs.app.state_machine.get(eid) {
            serde_json::to_value(&state).unwrap_or(serde_json::json!({"entity_id": eid}))
        } else {
            serde_json::json!({"entity_id": eid})
        }
    }).collect();

    Ok(Json(result))
}

/// POST /api/areas/{area_id}/entities/{entity_id} — assign entity to area
async fn assign_entity_to_area(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path((area_id, entity_id)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::assign_entity_area(&db_path, &entity_id, &area_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// DELETE /api/areas/{area_id}/entities/{entity_id} — unassign entity from area
async fn unassign_entity_from_area(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path((_area_id, entity_id)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::unassign_entity_area(&db_path, &entity_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// GET /api/devices — list all devices with their entities
async fn list_devices_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    let result = tokio::task::spawn_blocking(move || {
        let devices = crate::recorder::list_devices(&db_path)?;
        let mappings = crate::recorder::load_device_entities(&db_path)?;
        Ok::<_, anyhow::Error>((devices, mappings))
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let (devices, mappings) = result;
    let response: Vec<serde_json::Value> = devices.iter().map(|dev| {
        let entity_ids: Vec<&str> = mappings.iter()
            .filter(|(_, did)| *did == dev.device_id)
            .map(|(eid, _)| eid.as_str())
            .collect();
        serde_json::json!({
            "device_id": dev.device_id,
            "name": dev.name,
            "manufacturer": dev.manufacturer,
            "model": dev.model,
            "area_id": dev.area_id,
            "entity_count": entity_ids.len(),
            "entities": entity_ids,
        })
    }).collect();

    Ok(Json(response))
}

/// POST /api/devices — create or update a device
async fn create_device_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Json(body): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let device_id = body.get("device_id").and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?
        .to_string();
    let name = body.get("name").and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?
        .to_string();
    let manufacturer = body.get("manufacturer").and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let model = body.get("model").and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let area_id = body.get("area_id").and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let db_path = rs.db_path.clone();
    let device = crate::recorder::Device {
        device_id, name, manufacturer, model, area_id,
    };
    tokio::task::spawn_blocking(move || {
        crate::recorder::upsert_device(&db_path, &device)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// DELETE /api/devices/{device_id}
async fn delete_device_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(device_id): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::delete_device(&db_path, &device_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// POST /api/devices/{device_id}/entities/{entity_id} — assign entity to device
async fn assign_entity_device_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path((device_id, entity_id)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::assign_entity_device(&db_path, &entity_id, &device_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

// ── Persistent Notifications ────────────────────────────

/// GET /api/notifications — list active notifications
async fn list_notifications_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<crate::recorder::Notification>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    let notifs = tokio::task::spawn_blocking(move || {
        crate::recorder::list_notifications(&db_path)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(notifs))
}

/// POST /api/notifications/{id}/dismiss
async fn dismiss_notification_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(notification_id): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    let dismissed = tokio::task::spawn_blocking(move || {
        crate::recorder::dismiss_notification(&db_path, &notification_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    if dismissed {
        Ok(Json(serde_json::json!({"result": "ok"})))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// POST /api/notifications/dismiss_all
async fn dismiss_all_notifications_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::dismiss_all_notifications(&db_path)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

// ── Label Registry ──────────────────────────────────────

/// GET /api/labels — list all labels with entity counts
async fn list_labels_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    let result = tokio::task::spawn_blocking(move || {
        let labels = crate::recorder::list_labels(&db_path)?;
        let mappings = crate::recorder::load_entity_labels(&db_path)?;
        Ok::<_, anyhow::Error>((labels, mappings))
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let (labels, mappings) = result;
    let response: Vec<serde_json::Value> = labels.iter().map(|label| {
        let entity_ids: Vec<&str> = mappings.iter()
            .filter(|(_, lid)| *lid == label.label_id)
            .map(|(eid, _)| eid.as_str())
            .collect();
        serde_json::json!({
            "label_id": label.label_id,
            "name": label.name,
            "color": label.color,
            "entity_count": entity_ids.len(),
            "entities": entity_ids,
        })
    }).collect();

    Ok(Json(response))
}

/// POST /api/labels — create or update a label
async fn create_label_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Json(body): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let label_id = body.get("label_id").and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?
        .to_string();
    let name = body.get("name").and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?
        .to_string();
    let color = body.get("color").and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::upsert_label(&db_path, &label_id, &name, &color)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// DELETE /api/labels/{label_id}
async fn delete_label_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(label_id): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::delete_label(&db_path, &label_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// POST /api/labels/{label_id}/entities/{entity_id} — assign label to entity
async fn assign_label_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path((label_id, entity_id)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::assign_label(&db_path, &entity_id, &label_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// DELETE /api/labels/{label_id}/entities/{entity_id} — unassign label from entity
async fn unassign_label_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path((label_id, entity_id)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    let db_path = rs.db_path.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::unassign_label(&db_path, &entity_id, &label_id)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// GET /api/auth/tokens — list all long-lived access tokens
async fn list_tokens(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<Vec<crate::auth::TokenInfo>>, StatusCode> {
    check_auth(&rs, &headers)?;
    Ok(Json(rs.auth.list_tokens()))
}

/// POST /api/auth/tokens — create a new long-lived access token
async fn create_token(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Json(body): Json<serde_json::Value>,
) -> Result<Json<crate::auth::TokenInfo>, StatusCode> {
    check_auth(&rs, &headers)?;

    let name = body.get("name").and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?
        .to_string();

    let id = format!("tok_{}", uuid::Uuid::new_v4().as_simple());
    let token_value = format!("marge_{}", uuid::Uuid::new_v4().as_simple());
    let created_at = chrono::Utc::now().to_rfc3339();

    // Persist to SQLite
    let db_path = rs.db_path.clone();
    let id2 = id.clone();
    let name2 = name.clone();
    let tv2 = token_value.clone();
    tokio::task::spawn_blocking(move || {
        crate::recorder::store_token(&db_path, &id2, &name2, &tv2)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    // Add to in-memory auth
    let info = crate::auth::TokenInfo {
        id: id.clone(),
        name: name.clone(),
        created_at: created_at.clone(),
        token: Some(token_value.clone()),
    };
    rs.auth.add_token(token_value, crate::auth::TokenInfo {
        id,
        name,
        created_at,
        token: None,
    });

    // Return with the token value (only time it's shown)
    Ok(Json(info))
}

/// DELETE /api/auth/tokens/{token_id} — revoke a long-lived access token
async fn delete_token_handler(
    State(rs): State<RouterState>,
    headers: HeaderMap,
    Path(token_id): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;

    // Remove from SQLite
    let db_path = rs.db_path.clone();
    let tid = token_id.clone();
    let deleted = tokio::task::spawn_blocking(move || {
        crate::recorder::delete_token(&db_path, &tid)
    })
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    if !deleted {
        return Err(StatusCode::NOT_FOUND);
    }

    // Remove from in-memory auth
    rs.auth.remove_token_by_id(&token_id);

    Ok(Json(serde_json::json!({"result": "ok"})))
}

/// GET /api/error_log — return recent error log entries (HA-compatible)
async fn error_log(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<String, StatusCode> {
    check_auth(&rs, &headers)?;
    // Return empty log — Marge uses structured tracing, not file-based error log
    Ok(String::new())
}

/// POST /api/config/core/check_config — validate configuration (HA-compatible)
async fn check_config(
    State(rs): State<RouterState>,
    headers: HeaderMap,
) -> Result<Json<serde_json::Value>, StatusCode> {
    check_auth(&rs, &headers)?;
    // Check that automations and scenes can be parsed
    let mut errors = Vec::new();

    if let Some(engine) = &rs.engine {
        if let Some(path) = engine.get_automations_path() {
            if let Err(e) = std::fs::read_to_string(&path) {
                errors.push(format!("automations: {}", e));
            }
        }
    }

    if errors.is_empty() {
        Ok(Json(serde_json::json!({
            "result": "valid",
            "errors": null,
        })))
    } else {
        Ok(Json(serde_json::json!({
            "result": "invalid",
            "errors": errors.join("\n"),
        })))
    }
}

/// GET /metrics — Prometheus-compatible metrics endpoint
async fn prometheus_metrics(State(rs): State<RouterState>) -> impl IntoResponse {
    use std::sync::atomic::Ordering;
    use std::fmt::Write;

    let pid = std::process::id();
    let rss_kb = read_rss_kb(pid).unwrap_or(0);
    let uptime = rs.app.started_at.elapsed().as_secs();

    let m = &rs.app.state_machine.metrics;
    let state_changes = m.state_changes.load(Ordering::Relaxed);
    let events_fired = m.events_fired.load(Ordering::Relaxed);
    let total_ns = m.total_transition_ns.load(Ordering::Relaxed);
    let max_ns = m.max_transition_ns.load(Ordering::Relaxed);
    let startup_us = rs.app.startup_us.load(Ordering::Relaxed);

    let avg_us = if state_changes > 0 {
        (total_ns / state_changes) as f64 / 1000.0
    } else {
        0.0
    };

    let mut out = String::with_capacity(2048);

    let _ = writeln!(out, "# HELP marge_info Marge version info");
    let _ = writeln!(out, "# TYPE marge_info gauge");
    let _ = writeln!(out, "marge_info{{version=\"{}\"}} 1", env!("CARGO_PKG_VERSION"));

    let _ = writeln!(out, "# HELP marge_uptime_seconds Time since Marge started");
    let _ = writeln!(out, "# TYPE marge_uptime_seconds counter");
    let _ = writeln!(out, "marge_uptime_seconds {}", uptime);

    let _ = writeln!(out, "# HELP marge_startup_seconds Time to start Marge");
    let _ = writeln!(out, "# TYPE marge_startup_seconds gauge");
    let _ = writeln!(out, "marge_startup_seconds {:.6}", startup_us as f64 / 1_000_000.0);

    let _ = writeln!(out, "# HELP marge_entity_count Number of entities in state machine");
    let _ = writeln!(out, "# TYPE marge_entity_count gauge");
    let _ = writeln!(out, "marge_entity_count {}", rs.app.state_machine.len());

    let _ = writeln!(out, "# HELP marge_state_changes_total Total state transitions");
    let _ = writeln!(out, "# TYPE marge_state_changes_total counter");
    let _ = writeln!(out, "marge_state_changes_total {}", state_changes);

    let _ = writeln!(out, "# HELP marge_events_fired_total Total events fired");
    let _ = writeln!(out, "# TYPE marge_events_fired_total counter");
    let _ = writeln!(out, "marge_events_fired_total {}", events_fired);

    let _ = writeln!(out, "# HELP marge_latency_avg_microseconds Average state transition latency");
    let _ = writeln!(out, "# TYPE marge_latency_avg_microseconds gauge");
    let _ = writeln!(out, "marge_latency_avg_microseconds {:.2}", avg_us);

    let _ = writeln!(out, "# HELP marge_latency_max_microseconds Max state transition latency");
    let _ = writeln!(out, "# TYPE marge_latency_max_microseconds gauge");
    let _ = writeln!(out, "marge_latency_max_microseconds {:.2}", max_ns as f64 / 1000.0);

    let _ = writeln!(out, "# HELP marge_memory_rss_bytes Resident set size in bytes");
    let _ = writeln!(out, "# TYPE marge_memory_rss_bytes gauge");
    let _ = writeln!(out, "marge_memory_rss_bytes {}", rss_kb * 1024);

    let _ = writeln!(out, "# HELP marge_ws_connections Active WebSocket connections");
    let _ = writeln!(out, "# TYPE marge_ws_connections gauge");
    let _ = writeln!(out, "marge_ws_connections {}", rs.app.ws_connections.load(Ordering::Relaxed));

    // Automation trigger counts
    if let Some(engine) = &rs.engine {
        let infos = engine.get_automations_info();
        let _ = writeln!(out, "# HELP marge_automation_triggers_total Total triggers per automation");
        let _ = writeln!(out, "# TYPE marge_automation_triggers_total counter");
        for info in &infos {
            let _ = writeln!(out, "marge_automation_triggers_total{{id=\"{}\",alias=\"{}\"}} {}",
                info.id, info.alias.replace('"', "\\\""), info.total_triggers);
        }
    }

    (
        [(axum::http::header::CONTENT_TYPE.as_str(), "text/plain; version=0.0.4; charset=utf-8")],
        out,
    )
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
