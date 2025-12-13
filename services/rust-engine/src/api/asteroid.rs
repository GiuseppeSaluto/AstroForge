use axum::{extract::Json, http::StatusCode, response::IntoResponse};
use serde_json::json;

use crate::domain::asteroid::Asteroid;
use crate::domain::risk::RiskResult;
use crate::dto::asteroid_dto::AsteroidDTO;
use crate::logic::impact_energy::ImpactPhysics;

pub async fn process_asteroid(Json(dto): Json<AsteroidDTO>) -> impl IntoResponse {
    tracing::info!(id = %dto.id, name = %dto.name, "Processing asteroid request");

    let asteroid_domain = match Asteroid::try_from(dto) {
        Ok(a) => a,
        Err(err) => {
            tracing::error!("Validation failed: {}", err);
            let body = json!({ "error": "validation_failed", "details": err.to_string() });
            return (StatusCode::BAD_REQUEST, Json(body)).into_response();
        }
    };

    let volume_m3 = ImpactPhysics::volume_from_diameter_km(asteroid_domain.diameter_km);
    let mass = ImpactPhysics::mass_from_volume(
        volume_m3,
        crate::logic::impact_energy::AsteroidDensity::SType,
    );
    let energy_joules = ImpactPhysics::kinetic_energy_joules(mass, asteroid_domain.velocity_kps);
    let energy_megatons = ImpactPhysics::joules_to_megatons(energy_joules);
    let risk_score = ImpactPhysics::risk_score_from_energy(energy_joules);

    let result = RiskResult::new(
        asteroid_domain.id.clone(),
        asteroid_domain.name.clone(),
        energy_joules,
        energy_megatons,
        risk_score,
        asteroid_domain.hazardous,
        asteroid_domain.distance_km,
        asteroid_domain.velocity_kps,
        asteroid_domain.diameter_km,
    );
    
    tracing::info!(
        id = %asteroid_domain.id,
        name = %asteroid_domain.name,
        energy_megatons,
        risk_score,
        "Asteroid processed successfully"
    );
   

    (StatusCode::OK, Json(result)).into_response()
}
