mod api;
mod automation;
mod mqtt;
mod scene;
mod state;
mod websocket;

use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tracing_subscriber::EnvFilter;

use api::AppState;
use automation::AutomationEngine;
use scene::SceneEngine;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("info,marge=debug")),
        )
        .init();

    tracing::info!("Starting Marge v{}", env!("CARGO_PKG_VERSION"));

    // Initialize state machine (SSS §4.1.2)
    let state_machine = state::StateMachine::new(4096);

    let app_state = Arc::new(AppState {
        state_machine,
        started_at: std::time::Instant::now(),
    });

    // Load scenes (D7) — loaded before automations so engine can reference them
    let scenes_path = std::env::var("MARGE_SCENES_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/etc/marge/scenes.yaml"));

    let scene_engine = if scenes_path.exists() {
        match scene::load_scenes(&scenes_path) {
            Ok(scenes) => {
                let se = Arc::new(SceneEngine::new(scenes, app_state.clone()));
                for scene_id in se.scene_ids() {
                    app_state.state_machine.set(
                        format!("scene.{}", scene_id),
                        "scening".to_string(),
                        Default::default(),
                    );
                }
                Some(se)
            }
            Err(e) => {
                tracing::error!("Failed to load scenes from {:?}: {}", scenes_path, e);
                None
            }
        }
    } else {
        tracing::info!("No scenes file at {:?}", scenes_path);
        None
    };

    // Load automations (D4)
    let automations_path = std::env::var("MARGE_AUTOMATIONS_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/etc/marge/automations.yaml"));

    let engine = if automations_path.exists() {
        match automation::load_automations(&automations_path) {
            Ok(automations) => {
                let mut engine = AutomationEngine::new(automations, app_state.clone());
                // Wire scene engine into automation engine for scene.turn_on actions
                if let Some(se) = &scene_engine {
                    engine.set_scenes(se.clone());
                }
                let engine = Arc::new(engine);
                // Register automation entities
                for auto_id in engine.automation_ids() {
                    app_state.state_machine.set(
                        format!("automation.{}", auto_id),
                        "on".to_string(),
                        Default::default(),
                    );
                }
                Some(engine)
            }
            Err(e) => {
                tracing::error!("Failed to load automations from {:?}: {}", automations_path, e);
                None
            }
        }
    } else {
        tracing::info!("No automations file at {:?}", automations_path);
        None
    };

    // Store engine reference for the API to use (automation.trigger service)
    let engine_for_api = engine.clone();

    // Spawn automation event listener (D5)
    if let Some(engine) = engine.clone() {
        let mut rx = app_state.state_machine.subscribe();
        tokio::spawn(async move {
            loop {
                match rx.recv().await {
                    Ok(event) => {
                        engine.on_state_changed(&event).await;
                    }
                    Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => {
                        tracing::warn!("Automation listener lagged by {} events", n);
                    }
                    Err(tokio::sync::broadcast::error::RecvError::Closed) => {
                        break;
                    }
                }
            }
        });
    }

    // Start embedded MQTT broker
    let mqtt_port: u16 = std::env::var("MARGE_MQTT_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(1884);

    match mqtt::start_mqtt(app_state.clone(), mqtt_port) {
        Ok((_broker_handle, _subscriber_handle)) => {
            tracing::info!("Embedded MQTT broker on port {}", mqtt_port);
        }
        Err(e) => {
            tracing::warn!("Failed to start MQTT broker: {} — running without MQTT", e);
        }
    }

    // Build combined router: REST API + WebSocket
    let app = api::router(app_state.clone(), engine_for_api, scene_engine)
        .merge(websocket::router(app_state.clone()));

    // Bind to configured port
    let port: u16 = std::env::var("MARGE_HTTP_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8124);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("Listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
