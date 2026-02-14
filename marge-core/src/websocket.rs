use axum::{
    extract::{State, WebSocketUpgrade},
    response::IntoResponse,
    routing::get,
    Router,
};
use axum::extract::ws::{Message, WebSocket};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::mpsc;

use crate::api::AppState;
use crate::auth::AuthConfig;
use crate::automation::AutomationEngine;
use crate::scene::SceneEngine;
use crate::services::ServiceRegistry;
use crate::state::StateChangedEvent;

/// WebSocket message types (SSS §5.1.2 — HA WebSocket API compatible)
#[derive(Debug, Serialize)]
#[serde(tag = "type")]
enum WsOutgoing {
    #[serde(rename = "auth_required")]
    AuthRequired { ha_version: String },
    #[serde(rename = "auth_ok")]
    AuthOk { ha_version: String },
    #[serde(rename = "auth_invalid")]
    AuthInvalid { message: String },
    #[serde(rename = "result")]
    Result { id: u64, success: bool, result: Option<serde_json::Value> },
    #[serde(rename = "event")]
    Event { id: u64, event: serde_json::Value },
}

#[derive(Debug, Deserialize)]
struct WsIncoming {
    id: Option<u64>,
    #[serde(rename = "type")]
    msg_type: String,
    access_token: Option<String>,
    #[serde(flatten)]
    data: serde_json::Value,
}

/// Combined WebSocket state
#[derive(Clone)]
struct WsState {
    app: Arc<AppState>,
    auth: Arc<AuthConfig>,
    services: Arc<std::sync::RwLock<ServiceRegistry>>,
    db_path: std::path::PathBuf,
    engine: Option<Arc<AutomationEngine>>,
    scenes: Option<Arc<SceneEngine>>,
}

pub fn router(
    state: Arc<AppState>,
    auth: Arc<AuthConfig>,
    services: Arc<std::sync::RwLock<ServiceRegistry>>,
    db_path: std::path::PathBuf,
    engine: Option<Arc<AutomationEngine>>,
    scenes: Option<Arc<SceneEngine>>,
) -> Router {
    let ws_state = WsState { app: state, auth, services, db_path, engine, scenes };
    Router::new()
        .route("/api/websocket", get(ws_handler))
        .with_state(ws_state)
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(ws_state): State<WsState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| {
        handle_ws(socket, ws_state.app, ws_state.auth, ws_state.services,
                  ws_state.db_path, ws_state.engine, ws_state.scenes)
    })
}

/// RAII guard to decrement ws_connections on drop.
struct WsConnectionGuard(Arc<AppState>);
impl Drop for WsConnectionGuard {
    fn drop(&mut self) {
        self.0.ws_connections.fetch_sub(1, std::sync::atomic::Ordering::Relaxed);
    }
}

async fn handle_ws(
    mut socket: WebSocket,
    app: Arc<AppState>,
    auth: Arc<AuthConfig>,
    services: Arc<std::sync::RwLock<ServiceRegistry>>,
    db_path: std::path::PathBuf,
    engine: Option<Arc<AutomationEngine>>,
    scenes: Option<Arc<SceneEngine>>,
) {
    app.ws_connections.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let _guard = WsConnectionGuard(app.clone());

    // Send auth_required
    let auth_req = serde_json::to_string(&WsOutgoing::AuthRequired {
        ha_version: env!("CARGO_PKG_VERSION").to_string(),
    }).unwrap_or_default();
    if socket.send(Message::Text(auth_req)).await.is_err() {
        return;
    }

    // Wait for auth message
    let auth_msg = match socket.recv().await {
        Some(Ok(Message::Text(text))) => text,
        _ => return,
    };

    // Validate auth token
    let parsed: Result<WsIncoming, _> = serde_json::from_str(&auth_msg);
    match parsed {
        Ok(msg) if msg.msg_type == "auth" => {
            let token = msg.access_token.as_deref().unwrap_or("");
            if auth.validate(token) {
                let auth_ok = serde_json::to_string(&WsOutgoing::AuthOk {
                    ha_version: env!("CARGO_PKG_VERSION").to_string(),
                }).unwrap_or_default();
                if socket.send(Message::Text(auth_ok)).await.is_err() {
                    return;
                }
            } else {
                let auth_invalid = serde_json::to_string(&WsOutgoing::AuthInvalid {
                    message: "Invalid access token".to_string(),
                }).unwrap_or_default();
                let _ = socket.send(Message::Text(auth_invalid)).await;
                return;
            }
        }
        _ => return,
    }

    // Use a channel to bridge state_changed events into the socket loop.
    // We spawn a task that reads from the broadcast receiver and forwards
    // into an mpsc, so we can select! on both the socket and state events.
    let (event_tx, mut event_rx) = mpsc::channel::<StateChangedEvent>(256);
    let mut state_rx = app.state_machine.subscribe();
    tokio::spawn(async move {
        while let Ok(event) = state_rx.recv().await {
            if event_tx.send(event).await.is_err() {
                break;
            }
        }
    });

    // Track which subscription IDs want state_changed events
    let mut subscribed_ids: Vec<u64> = Vec::new();

    loop {
        tokio::select! {
            // Handle incoming messages from client
            msg = socket.recv() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        if let Ok(incoming) = serde_json::from_str::<WsIncoming>(&text) {
                            let id = incoming.id.unwrap_or(0);
                            let resp = match incoming.msg_type.as_str() {
                                "subscribe_events" => {
                                    subscribed_ids.push(id);
                                    ws_result(id, true, None)
                                }
                                "unsubscribe_events" => {
                                    let unsub_id = incoming.data.get("subscription")
                                        .and_then(|v| v.as_u64()).unwrap_or(0);
                                    subscribed_ids.retain(|&sid| sid != unsub_id);
                                    ws_result(id, true, None)
                                }
                                "render_template" => {
                                    let template = incoming.data.get("template")
                                        .and_then(|v| v.as_str()).unwrap_or("");
                                    match crate::template::render_with_state_machine(template, &app.state_machine) {
                                        Ok(rendered) => ws_result(id, true, Some(serde_json::json!({"result": rendered}))),
                                        Err(e) => ws_result(id, false, Some(serde_json::json!({"message": e}))),
                                    }
                                }
                                "get_states" => {
                                    let states = app.state_machine.get_all();
                                    ws_result(id, true, Some(serde_json::to_value(&states).unwrap_or_default()))
                                }
                                "call_service" => {
                                    // HA-compatible: { domain, service, service_data: { entity_id, ... } }
                                    let data = &incoming.data;
                                    let domain = data.get("domain").and_then(|v| v.as_str()).unwrap_or("");
                                    let service = data.get("service").and_then(|v| v.as_str()).unwrap_or("");
                                    let svc_data = data.get("service_data").cloned().unwrap_or(serde_json::Value::Object(Default::default()));
                                    let entity_id_str = svc_data.get("entity_id").and_then(|v| v.as_str()).unwrap_or("");

                                    // Handle automation services specially (need engine access)
                                    if domain == "automation" {
                                        if let Some(eng) = &engine {
                                            match service {
                                                "trigger" => { eng.trigger_by_id(entity_id_str).await; }
                                                "turn_on" => { eng.set_enabled(entity_id_str, true); }
                                                "turn_off" => { eng.set_enabled(entity_id_str, false); }
                                                "toggle" => {
                                                    let aid = entity_id_str.strip_prefix("automation.").unwrap_or(entity_id_str);
                                                    let enabled = eng.get_automations_info()
                                                        .iter().find(|a| a.id == aid).map(|a| a.enabled).unwrap_or(true);
                                                    eng.set_enabled(entity_id_str, !enabled);
                                                }
                                                _ => {}
                                            }
                                        }
                                        ws_result(id, true, Some(serde_json::json!([])))
                                    } else if domain == "scene" && service == "turn_on" {
                                        if let Some(se) = &scenes {
                                            se.turn_on(entity_id_str);
                                        }
                                        ws_result(id, true, Some(serde_json::json!([])))
                                    } else if domain == "persistent_notification" {
                                        match service {
                                            "create" => {
                                                let notif_id = svc_data.get("notification_id")
                                                    .and_then(|v| v.as_str()).unwrap_or("auto").to_string();
                                                let notif_id = if notif_id == "auto" {
                                                    uuid::Uuid::new_v4().to_string()
                                                } else { notif_id };
                                                let title = svc_data.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string();
                                                let message = svc_data.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string();
                                                let db = db_path.clone();
                                                let _ = tokio::task::spawn_blocking(move || {
                                                    crate::recorder::create_notification(&db, &notif_id, &title, &message)
                                                }).await;
                                            }
                                            "dismiss" => {
                                                let notif_id = svc_data.get("notification_id")
                                                    .and_then(|v| v.as_str()).unwrap_or("").to_string();
                                                let db = db_path.clone();
                                                let _ = tokio::task::spawn_blocking(move || {
                                                    crate::recorder::dismiss_notification(&db, &notif_id)
                                                }).await;
                                            }
                                            "dismiss_all" => {
                                                let db = db_path.clone();
                                                let _ = tokio::task::spawn_blocking(move || {
                                                    crate::recorder::dismiss_all_notifications(&db)
                                                }).await;
                                            }
                                            _ => {}
                                        }
                                        ws_result(id, true, Some(serde_json::json!([])))
                                    } else {
                                        // Standard service dispatch through registry
                                        // Support both service_data.entity_id and target.entity_id patterns
                                        let entity_ids: Vec<String> = match svc_data.get("entity_id") {
                                            Some(serde_json::Value::String(s)) => vec![s.clone()],
                                            Some(serde_json::Value::Array(arr)) => {
                                                arr.iter().filter_map(|v| v.as_str().map(String::from)).collect()
                                            }
                                            _ => match data.get("target").and_then(|t| t.get("entity_id")) {
                                                Some(serde_json::Value::String(s)) => vec![s.clone()],
                                                Some(serde_json::Value::Array(arr)) => {
                                                    arr.iter().filter_map(|v| v.as_str().map(String::from)).collect()
                                                }
                                                _ => vec![],
                                            },
                                        };
                                        let changed = {
                                            let registry = services.read().unwrap_or_else(|e| e.into_inner());
                                            registry.call(domain, service, &entity_ids, &svc_data, &app.state_machine)
                                        };
                                        ws_result(id, true, Some(serde_json::to_value(&changed).unwrap_or_default()))
                                    }
                                }
                                "fire_event" => {
                                    let event_type = incoming.data.get("event_type")
                                        .and_then(|v| v.as_str())
                                        .unwrap_or("unknown");
                                    tracing::info!(event_type = %event_type, "WS event fired");
                                    ws_result(id, true, None)
                                }
                                "get_services" => {
                                    let registry = services.read().unwrap_or_else(|e| e.into_inner());
                                    let svc_list = registry.list_domains_json();
                                    ws_result(id, true, Some(svc_list))
                                }
                                "get_config" => {
                                    let config = serde_json::json!({
                                        "location_name": "Marge Demo Home",
                                        "latitude": 40.3916,
                                        "longitude": -111.8508,
                                        "elevation": 1387,
                                        "unit_system": {
                                            "length": "mi",
                                            "mass": "lb",
                                            "temperature": "\u{00b0}F",
                                            "volume": "gal",
                                        },
                                        "time_zone": "America/Denver",
                                        "version": env!("CARGO_PKG_VERSION"),
                                        "state": "RUNNING",
                                    });
                                    ws_result(id, true, Some(config))
                                }
                                "get_notifications" => {
                                    let db = db_path.clone();
                                    let notifs = tokio::task::spawn_blocking(move || {
                                        crate::recorder::list_notifications(&db)
                                    }).await.ok().and_then(|r| r.ok()).unwrap_or_default();
                                    ws_result(id, true, Some(serde_json::to_value(&notifs).unwrap_or_default()))
                                }
                                "persistent_notification/dismiss" => {
                                    let notif_id = incoming.data.get("notification_id")
                                        .and_then(|v| v.as_str()).unwrap_or("").to_string();
                                    let db = db_path.clone();
                                    let ok = tokio::task::spawn_blocking(move || {
                                        crate::recorder::dismiss_notification(&db, &notif_id)
                                    }).await.ok().and_then(|r| r.ok()).unwrap_or(false);
                                    ws_result(id, ok, None)
                                }
                                "config/entity_registry/list" => {
                                    // HA-compatible entity registry: return minimal entries
                                    let states = app.state_machine.get_all();
                                    let entries: Vec<serde_json::Value> = states.iter().map(|s| {
                                        serde_json::json!({
                                            "entity_id": s.entity_id,
                                            "name": s.attributes.get("friendly_name").and_then(|v| v.as_str()).unwrap_or(""),
                                            "platform": "mqtt",
                                            "disabled_by": null,
                                        })
                                    }).collect();
                                    ws_result(id, true, Some(serde_json::to_value(&entries).unwrap_or_default()))
                                }
                                "config/area_registry/list" => {
                                    let db = db_path.clone();
                                    let areas = tokio::task::spawn_blocking(move || {
                                        crate::recorder::init_areas(&db)
                                    }).await.ok().and_then(|r| r.ok()).unwrap_or_default();
                                    ws_result(id, true, Some(serde_json::to_value(&areas).unwrap_or_default()))
                                }
                                "config/device_registry/list" => {
                                    let db = db_path.clone();
                                    let result = tokio::task::spawn_blocking(move || {
                                        let devices = crate::recorder::list_devices(&db)?;
                                        let mappings = crate::recorder::load_device_entities(&db)?;
                                        Ok::<_, anyhow::Error>((devices, mappings))
                                    }).await.ok().and_then(|r| r.ok());
                                    let entries: Vec<serde_json::Value> = match result {
                                        Some((devices, mappings)) => {
                                            devices.into_iter().map(|d| {
                                                let ents: Vec<&str> = mappings.iter()
                                                    .filter(|(_, did)| did == &d.device_id)
                                                    .map(|(eid, _)| eid.as_str())
                                                    .collect();
                                                serde_json::json!({
                                                    "id": d.device_id,
                                                    "name": d.name,
                                                    "manufacturer": d.manufacturer,
                                                    "model": d.model,
                                                    "area_id": d.area_id,
                                                    "entities": ents,
                                                })
                                            }).collect()
                                        }
                                        None => vec![],
                                    };
                                    ws_result(id, true, Some(serde_json::to_value(&entries).unwrap_or_default()))
                                }
                                "config/label_registry/list" => {
                                    let db = db_path.clone();
                                    let result = tokio::task::spawn_blocking(move || {
                                        let labels = crate::recorder::list_labels(&db)?;
                                        let mappings = crate::recorder::load_entity_labels(&db)?;
                                        Ok::<_, anyhow::Error>((labels, mappings))
                                    }).await.ok().and_then(|r| r.ok());
                                    let entries: Vec<serde_json::Value> = match result {
                                        Some((labels, mappings)) => {
                                            labels.into_iter().map(|l| {
                                                let ents: Vec<&str> = mappings.iter()
                                                    .filter(|(_, lid)| lid == &l.label_id)
                                                    .map(|(eid, _)| eid.as_str())
                                                    .collect();
                                                serde_json::json!({
                                                    "label_id": l.label_id,
                                                    "name": l.name,
                                                    "color": l.color,
                                                    "entities": ents,
                                                })
                                            }).collect()
                                        }
                                        None => vec![],
                                    };
                                    ws_result(id, true, Some(serde_json::to_value(&entries).unwrap_or_default()))
                                }
                                "ping" => {
                                    // HA-compatible pong response
                                    serde_json::to_string(&serde_json::json!({
                                        "id": id,
                                        "type": "pong",
                                    })).unwrap_or_default()
                                }
                                _ => {
                                    tracing::debug!(msg_type = %incoming.msg_type, "Unknown WS message type");
                                    ws_result(id, false, Some(serde_json::json!({"message": "Unknown command"})))
                                }
                            };
                            if socket.send(Message::Text(resp)).await.is_err() {
                                break;
                            }
                        }
                    }
                    Some(Ok(Message::Close(_))) | None => break,
                    _ => {}
                }
            }

            // Forward state_changed events to subscribers
            Some(event) = event_rx.recv() => {
                for &sub_id in &subscribed_ids {
                    let ws_event = serde_json::to_string(&WsOutgoing::Event {
                        id: sub_id,
                        event: make_state_changed_event(&event),
                    }).unwrap_or_default();
                    if socket.send(Message::Text(ws_event)).await.is_err() {
                        return;
                    }
                }
            }
        }
    }
}

fn ws_result(id: u64, success: bool, result: Option<serde_json::Value>) -> String {
    serde_json::to_string(&WsOutgoing::Result { id, success, result }).unwrap_or_default()
}

fn make_state_changed_event(event: &StateChangedEvent) -> serde_json::Value {
    serde_json::json!({
        "event_type": "state_changed",
        "data": {
            "entity_id": event.entity_id,
            "old_state": event.old_state,
            "new_state": event.new_state,
        },
        "time_fired": chrono::Utc::now().to_rfc3339(),
    })
}
