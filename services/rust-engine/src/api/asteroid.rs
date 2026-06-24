use axum::{extract::Json, http::StatusCode, response::IntoResponse};
use crate::domain::asteroid::Asteroid;
use crate::domain::error::map_domain_error;
use crate::domain::risk::RiskResult;
use crate::dto::asteroid_dto::AsteroidDTO;
use crate::logic::impact_energy::{AsteroidDensity, ImpactPhysics};

// ── Shared compute helper ─────────────────────────────────────────────────────

fn compute_risk(asteroid: &Asteroid) -> RiskResult {
    let volume_m3 = ImpactPhysics::volume_from_diameter_km(asteroid.diameter_km);
    let mass = ImpactPhysics::mass_from_volume(volume_m3, AsteroidDensity::SType);
    let energy_joules = ImpactPhysics::kinetic_energy_joules(mass, asteroid.velocity_kps);
    let energy_megatons = ImpactPhysics::joules_to_megatons(energy_joules);

    let base_score = ImpactPhysics::risk_score_from_energy(energy_joules);
    let score = ImpactPhysics::apply_proximity_factor(base_score, asteroid.distance_km);
    let score = ImpactPhysics::apply_hazardous_bonus(score, asteroid.hazardous);

    RiskResult::new(
        asteroid.id.clone(),
        asteroid.name.clone(),
        energy_joules,
        energy_megatons,
        score,
        asteroid.hazardous,
        asteroid.distance_km,
        asteroid.velocity_kps,
        asteroid.diameter_km,
    )
}

// ── Single asteroid ───────────────────────────────────────────────────────────

pub async fn process_asteroid(Json(dto): Json<AsteroidDTO>) -> impl IntoResponse {
    tracing::info!(id = %dto.id, name = %dto.name, "Processing single asteroid");

    let asteroid = match Asteroid::try_from(dto) {
        Ok(a) => a,
        Err(err) => {
            tracing::warn!("Validation failed: {}", err);
            return map_domain_error(err).into_response();
        }
    };

    let result = compute_risk(&asteroid);

    tracing::info!(
        id = %asteroid.id,
        risk_score = result.risk_score_0_to_100,
        energy_mt = result.impact_energy_megatons,
        "Single asteroid processed"
    );

    (StatusCode::OK, Json(result)).into_response()
}

// ── Batch ─────────────────────────────────────────────────────────────────────

pub async fn process_asteroid_batch(Json(dtos): Json<Vec<AsteroidDTO>>) -> impl IntoResponse {
    if dtos.is_empty() {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "error": "empty_batch",
                "details": "Batch must contain at least one asteroid"
            })),
        )
            .into_response();
    }

    if dtos.len() > 500 {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "error": "batch_too_large",
                "details": "Batch size cannot exceed 500"
            })),
        )
            .into_response();
    }

    tracing::info!(count = dtos.len(), "Processing asteroid batch");

    let results: Vec<RiskResult> = dtos
        .into_iter()
        .filter_map(|dto| {
            let id = dto.id.clone();
            match Asteroid::try_from(dto) {
                Ok(asteroid) => Some(compute_risk(&asteroid)),
                Err(err) => {
                    tracing::warn!(id = %id, error = %err, "Skipping asteroid: validation failed");
                    None
                }
            }
        })
        .collect();

    tracing::info!(processed = results.len(), "Batch complete");

    (StatusCode::OK, Json(results)).into_response()
}
