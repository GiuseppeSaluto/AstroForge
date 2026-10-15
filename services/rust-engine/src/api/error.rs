use axum::{http::StatusCode, response::IntoResponse, Json};
use serde_json::json;

use crate::domain::error::DomainError;

pub fn map_domain_error(err: DomainError) -> impl IntoResponse {
    // Every variant is bad input today, but the match is kept exhaustive
    // (no `_` arm) on purpose: adding a new DomainError variant then fails
    // to compile here until someone decides which HTTP status it maps to.
    let (status, error_type) = match err {
        DomainError::InvalidId
        | DomainError::InvalidDiameter(_)
        | DomainError::InvalidVelocity(_)
        | DomainError::InvalidField(_) => (StatusCode::BAD_REQUEST, "invalid_input"),
    };

    let body = json!({
        "error": error_type,
        "details": err.to_string()
    });

    (status, Json(body))
}
