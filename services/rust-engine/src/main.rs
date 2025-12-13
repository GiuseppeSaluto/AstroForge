use axum::{Router};
use std::net::SocketAddr;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod api;
mod domain;
mod dto;
mod logic;

#[tokio::main]
async fn main() {
    // Tracing / logging basic setup
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Build the application router
    let api_router = api::router();

    let app = Router::new()
        .nest("/api", api_router)
        .layer(TraceLayer::new_for_http());

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    tracing::info!("Starting Rust engine on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
