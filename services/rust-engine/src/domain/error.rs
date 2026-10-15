use thiserror::Error;

#[derive(Error, Debug)]
pub enum DomainError {
    #[error("Invalid or empty asteroid ID")]
    InvalidId,

    #[error("Invalid diameter: {0} km (must be > 0)")]
    InvalidDiameter(f64),

    #[error("Invalid velocity magnitude: {0} km/s (must be >= 0)")]
    InvalidVelocity(f64),

    #[error("Invalid or missing field: {0}")]
    InvalidField(&'static str),
}
