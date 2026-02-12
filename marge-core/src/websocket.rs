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
use crate::state::StateChangedEvent;

/// WebSocket message types (SSS §5.1.2 — HA WebSocket API compatible)
#[derive(Debug, Serialize)]
#[serde(tag = "type")]
enum WsOutgoing {
    #[serde(rename = "auth_required")]
    AuthRequired { ha_version: String },
    #[serde(rename = "auth_ok")]
    AuthOk { ha_version: String },
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
    #[serde(flatten)]
    _data: serde_json::Value,
}

pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/api/websocket", get(ws_handler))
        .with_state(state)
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(app): State<Arc<AppState>>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_ws(socket, app))
}

async fn handle_ws(mut socket: WebSocket, app: Arc<AppState>) {
    // Send auth_required
    let auth_req = serde_json::to_string(&WsOutgoing::AuthRequired {
        ha_version: env!("CARGO_PKG_VERSION").to_string(),
    }).unwrap();
    if socket.send(Message::Text(auth_req)).await.is_err() {
        return;
    }

    // Wait for auth message
    let auth_msg = match socket.recv().await {
        Some(Ok(Message::Text(text))) => text,
        _ => return,
    };

    // Accept any auth (demo mode — no real auth)
    let parsed: Result<WsIncoming, _> = serde_json::from_str(&auth_msg);
    if let Ok(msg) = parsed {
        if msg.msg_type == "auth" {
            let auth_ok = serde_json::to_string(&WsOutgoing::AuthOk {
                ha_version: env!("CARGO_PKG_VERSION").to_string(),
            }).unwrap();
            if socket.send(Message::Text(auth_ok)).await.is_err() {
                return;
            }
        }
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
                                "get_states" => {
                                    let states = app.state_machine.get_all();
                                    ws_result(id, true, Some(serde_json::to_value(&states).unwrap()))
                                }
                                "ping" => {
                                    ws_result(id, true, None)
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
                    }).unwrap();
                    if socket.send(Message::Text(ws_event)).await.is_err() {
                        return;
                    }
                }
            }
        }
    }
}

fn ws_result(id: u64, success: bool, result: Option<serde_json::Value>) -> String {
    serde_json::to_string(&WsOutgoing::Result { id, success, result }).unwrap()
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
