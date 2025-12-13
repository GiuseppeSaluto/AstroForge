use axum::{extract::Json, http::StatusCode, response::IntoResponse};
use crate::domain::asteroid::Asteroid;
use crate::domain::error::map_domain_error;
use crate::domain::risk::RiskResult;
use crate::dto::asteroid_dto::AsteroidDTO;
use crate::logic::impact_energy::ImpactPhysics;

pub async fn process_asteroid(Json(dto): Json<AsteroidDTO>) -> impl IntoResponse {
    tracing::info!(id = %dto.id, name = %dto.name, "Processing asteroid request");

    let asteroid = match Asteroid::try_from(dto) {
        Ok(a) => a,
        Err(err) => {
            tracing::warn!("Domain validation failed: {}", err);
            return map_domain_error(err).into_response();
        }
    };

    let volume_m3 = ImpactPhysics::volume_from_diameter_km(asteroid.diameter_km);
    let mass = ImpactPhysics::mass_from_volume(
        volume_m3,
        crate::logic::impact_energy::AsteroidDensity::SType,
    );
    let energy_joules = ImpactPhysics::kinetic_energy_joules(mass, asteroid.velocity_kps);
    let energy_megatons = ImpactPhysics::joules_to_megatons(energy_joules);
    let risk_score = ImpactPhysics::risk_score_from_energy(energy_joules);

    let result = RiskResult::new(
        asteroid.id.clone(),
        asteroid.name.clone(),
        energy_joules,
        energy_megatons,
        risk_score,
        asteroid.hazardous,
        asteroid.distance_km,
        asteroid.velocity_kps,
        asteroid.diameter_km,
    );
    
    tracing::info!(
        id = %asteroid.id,
        name = %asteroid.name,
        energy_megatons,
        risk_score,
        "Asteroid processed successfully"
    );
   

    (StatusCode::OK, Json(result)).into_response()
}
