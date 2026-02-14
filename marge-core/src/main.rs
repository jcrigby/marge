mod api;
mod auth;
mod automation;
mod discovery;
mod integrations;
mod mqtt;
mod recorder;
mod scene;
mod services;
mod state;
mod template;
mod websocket;

use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tracing_subscriber::EnvFilter;

use api::AppState;
use auth::AuthConfig;
use automation::AutomationEngine;
use scene::SceneEngine;
use services::ServiceRegistry;

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

    // ── Authentication (Phase 4 §4.3) ──────────────────────
    let auth = Arc::new(AuthConfig::from_env());

    // Initialize state machine (SSS §4.1.2)
    let state_machine = state::StateMachine::new(4096);

    // ── State Persistence (Phase 2 §1.1) ─────────────────
    let db_path = std::env::var("MARGE_DB_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/data/marge.db"));

    // Ensure parent directory exists
    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent).ok();
    }

    let _restored = match recorder::restore(&db_path, &state_machine) {
        Ok(n) => {
            tracing::info!("Restored {} entity states from {:?}", n, db_path);
            n
        }
        Err(e) => {
            tracing::warn!("State restore failed: {} — starting fresh", e);
            0
        }
    };

    // Load long-lived access tokens from DB
    match recorder::init_tokens(&db_path) {
        Ok(tokens) => {
            let count = tokens.len();
            for (token_value, stored) in tokens {
                auth.add_token(token_value, auth::TokenInfo {
                    id: stored.id,
                    name: stored.name,
                    created_at: stored.created_at,
                    token: None,
                });
            }
            if count > 0 {
                tracing::info!("Loaded {} long-lived access tokens", count);
            }
        }
        Err(e) => {
            tracing::warn!("Failed to load access tokens: {}", e);
        }
    }

    let retention_days: u32 = std::env::var("MARGE_HISTORY_DAYS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(10);
    let db_path_for_api = db_path.clone();
    let db_path_for_ws = db_path.clone();
    let recorder_tx = recorder::spawn_writer(db_path, retention_days);

    let app_state = Arc::new(AppState {
        state_machine,
        started_at: std::time::Instant::now(),
        startup_us: std::sync::atomic::AtomicU64::new(0),
        sim_time: std::sync::Mutex::new(String::new()),
        sim_chapter: std::sync::Mutex::new(String::new()),
        sim_speed: std::sync::atomic::AtomicU32::new(0),
        ws_connections: std::sync::atomic::AtomicU32::new(0),
    });

    // ── Service Registry (Phase 2 §1.4) ──────────────────
    let service_registry = Arc::new(std::sync::RwLock::new(ServiceRegistry::new()));

    // ── Discovery Engine (Phase 2 §1.2) ──────────────────
    let mqtt_targets = service_registry.read().unwrap_or_else(|e| e.into_inner()).mqtt_targets();
    let discovery_engine = Arc::new(discovery::DiscoveryEngine::new(
        app_state.clone(),
        mqtt_targets,
    ));

    // ── Device Bridge Managers (Phase 2 §2.1-2.3) ───────
    let z2m_bridge = Arc::new(integrations::zigbee2mqtt::Zigbee2MqttBridge::new(app_state.clone()));
    let zwave_bridge = Arc::new(integrations::zwave::ZwaveBridge::new(app_state.clone()));
    let tasmota_bridge = Arc::new(integrations::tasmota::TasmotaBridge::new(app_state.clone()));
    let esphome_bridge = Arc::new(integrations::esphome::ESPHomeBridge::new(app_state.clone()));

    // Load scenes (D7) — loaded before automations so engine can reference them
    let scenes_path = std::env::var("MARGE_SCENES_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/etc/marge/scenes.yaml"));

    let scene_engine = if scenes_path.exists() {
        match scene::load_scenes(&scenes_path) {
            Ok(scenes) => {
                let se = Arc::new(SceneEngine::new(scenes, app_state.clone()));
                for (scene_id, scene_name) in se.scene_ids() {
                    let mut attrs = serde_json::Map::new();
                    attrs.insert("friendly_name".to_string(), serde_json::json!(scene_name));
                    app_state.state_machine.set(
                        format!("scene.{}", scene_id),
                        "scening".to_string(),
                        attrs,
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
                let engine = AutomationEngine::new(automations, app_state.clone(), service_registry.clone());
                // Wire scene engine into automation engine for scene.turn_on actions
                if let Some(se) = &scene_engine {
                    engine.set_scenes(se.clone());
                }
                engine.set_automations_path(automations_path.clone());
                let engine = Arc::new(engine);
                // Register automation entities with friendly_name attribute
                for (auto_id, alias) in engine.automation_ids() {
                    let mut attrs = serde_json::Map::new();
                    attrs.insert("friendly_name".to_string(), serde_json::json!(alias));
                    attrs.insert("current".to_string(), serde_json::json!(0));
                    app_state.state_machine.set(
                        format!("automation.{}", auto_id),
                        "on".to_string(),
                        attrs,
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

    // ── Persistence writer: feed state changes ───────────
    {
        let recorder_tx = recorder_tx.clone();
        let mut rx = app_state.state_machine.subscribe();
        tokio::spawn(async move {
            loop {
                match rx.recv().await {
                    Ok(event) => {
                        let _ = recorder_tx.send(event);
                    }
                    Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => {
                        tracing::warn!("Recorder listener lagged by {} events", n);
                    }
                    Err(tokio::sync::broadcast::error::RecvError::Closed) => break,
                }
            }
        });
    }

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

    // Spawn time/sun trigger evaluation loop (Phase 3 §3.1-3.2)
    if let Some(engine) = engine.clone() {
        tokio::spawn(async move {
            engine.run_time_loop().await;
        });
    }

    // Start embedded MQTT broker
    let mqtt_port: u16 = std::env::var("MARGE_MQTT_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(1884);

    let bridges = mqtt::DeviceBridges {
        z2m: z2m_bridge,
        zwave: zwave_bridge,
        tasmota: tasmota_bridge,
        esphome: esphome_bridge,
    };
    match mqtt::start_mqtt(app_state.clone(), mqtt_port, discovery_engine.clone(), bridges) {
        Ok((_broker_handle, _subscriber_handle)) => {
            tracing::info!("Embedded MQTT broker on port {}", mqtt_port);
        }
        Err(e) => {
            tracing::warn!("Failed to start MQTT broker: {} — running without MQTT", e);
        }
    }

    // Build combined router: REST API + WebSocket
    let service_registry_for_ws = service_registry.clone();
    let mut app = api::router(
        app_state.clone(),
        engine_for_api,
        scene_engine,
        service_registry,
        auth.clone(),
        db_path_for_api,
        automations_path,
        scenes_path,
    )
    .merge(websocket::router(app_state.clone(), auth.clone(), service_registry_for_ws, db_path_for_ws));

    // ── Static File Serving (Phase 4 §4.1) ─────────────────
    let dashboard_path = std::env::var("MARGE_DASHBOARD_PATH")
        .unwrap_or_else(|_| "/usr/share/marge/ui".to_string());
    if std::path::Path::new(&dashboard_path).exists() {
        tracing::info!("Serving dashboard from {:?}", dashboard_path);
        app = app.fallback_service(
            tower_http::services::ServeDir::new(&dashboard_path)
                .fallback(tower_http::services::ServeFile::new(
                    format!("{}/index.html", dashboard_path),
                )),
        );
    }

    // Bind to configured port
    let port: u16 = std::env::var("MARGE_HTTP_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8124);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));

    let listener = tokio::net::TcpListener::bind(addr).await?;

    // Record startup time (microseconds for sub-ms precision)
    let startup_us = app_state.started_at.elapsed().as_micros() as u64;
    app_state.startup_us.store(startup_us, std::sync::atomic::Ordering::Relaxed);
    tracing::info!("Listening on {} (startup: {}us / {:.1}ms)", addr, startup_us, startup_us as f64 / 1000.0);

    // ── Graceful Shutdown (Phase 6 §6.1) ────────────────────
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    tracing::info!("Marge shutdown complete");
    Ok(())
}

/// Wait for SIGTERM or SIGINT for graceful shutdown.
async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => { tracing::info!("Received SIGINT, shutting down"); }
        _ = terminate => { tracing::info!("Received SIGTERM, shutting down"); }
    }
}
