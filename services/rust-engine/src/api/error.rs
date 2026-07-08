use axum::{http::StatusCode, response::IntoResponse, Json};
use serde_json::json;

use crate::domain::error::DomainError;

pub fn map_domain_error(err: DomainError) -> impl IntoResponse {
    let (status, error_type) = match err {
        DomainError::InvalidId
        | DomainError::InvalidDiameter(_)
        | DomainError::InvalidVelocity(_)
        | DomainError::InvalidField(_) => {
            (StatusCode::BAD_REQUEST, "invalid_input")
        }

        DomainError::MissingCloseApproachData
        | DomainError::NonPhysicalValue { .. } => {
            (StatusCode::UNPROCESSABLE_ENTITY, "invalid_domain_data")
        }
    };

    let body = json!({
        "error": error_type,
        "details": err.to_string()
    });

    (status, Json(body))
}
