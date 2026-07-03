use axum::{Router};
use std::net::SocketAddr;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod api;
mod domain;
mod dto;
mod logic;

/// Reads the listen port from the `RUST_PORT` env var (matches
/// `infra/env/rust.env`), falling back to 8080 if it's unset or not a
/// valid number.
fn resolve_port() -> u16 {
    match std::env::var("RUST_PORT") {
        Ok(value) => match value.parse::<u16>() {
            Ok(port) => port,
            Err(_) => {
                tracing::warn!("RUST_PORT env var set but not a valid number ('{value}'), falling back to 8080");
                8080
            }
        },
        Err(_) => 8080,
    }
}

#[tokio::main]
async fn main() {
    // Loads a .env file into the process environment if one is found
    // (searches the current dir and its ancestors, like Python's
    // `load_dotenv(find_dotenv())`). In Docker, `env_file:` already sets
    // these vars directly, so there's no .env to find and this is a no-op.
    dotenvy::dotenv().ok();

    // Tracing / logging basic setup
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Build the application router
    let api_router = api::router();

    let app = Router::new()
        .nest("/api", api_router)
        .layer(TraceLayer::new_for_http());

    let port = resolve_port();
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("Starting Rust engine on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .unwrap_or_else(|err| panic!("Failed to bind to {addr}: {err}"));
    axum::serve(listener, app).await.expect("Failed to serve");
}
