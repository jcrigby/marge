mod api;
mod state;
mod websocket;

use std::net::SocketAddr;
use std::sync::Arc;
use tracing_subscriber::EnvFilter;

use api::AppState;

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

    let app_state = Arc::new(AppState { state_machine });

    // Build combined router: REST API + WebSocket
    let app = api::router(app_state.clone())
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
