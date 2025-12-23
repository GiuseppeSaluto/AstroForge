use axum::Router;
use axum::routing::{get, post};
mod asteroid;

pub use asteroid::process_asteroid;

async fn health() -> &'static str {
    "ok"
}

pub fn router() -> Router {
    Router::new()
    .route("/health", get(health))
    .route("/api/process/asteroid", post(process_asteroid))

}
