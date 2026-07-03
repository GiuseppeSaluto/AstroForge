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

// ── Integration tests ──────────────────────────────────────────────────────
//
// Unlike the unit tests in `logic/impact_energy.rs` and `domain/asteroid.rs`
// (which call plain functions), these drive the actual Axum `Router` with
// real HTTP requests via `tower::ServiceExt::oneshot`. No TCP socket is
// opened — the request is passed straight into the router in-process.
#[cfg(test)]
mod integration_tests {
    use crate::api::router;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;

    fn valid_asteroid_json() -> serde_json::Value {
        serde_json::json!({
            "id": "12345",
            "name": "Test Asteroid",
            "absolute_magnitude_h": 20.0,
            "diameter_min_km": 0.1,
            "diameter_max_km": 0.5,
            "diameter_avg_km": 0.3,
            "close_approach_date": "2025-01-01",
            "relative_velocity_kps": 10.0,
            "miss_distance_km": 100_000.0,
            "orbiting_body": "Earth",
            "is_potentially_hazardous": false
        })
    }

    fn post_request(uri: &str, body: serde_json::Value) -> Request<Body> {
        Request::builder()
            .method("POST")
            .uri(uri)
            .header("content-type", "application/json")
            .body(Body::from(body.to_string()))
            .unwrap()
    }

    #[tokio::test]
    async fn health_check_returns_ok() {
        let request = Request::builder()
            .uri("/health")
            .body(Body::empty())
            .unwrap();

        let response = router().oneshot(request).await.unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn process_asteroid_returns_200_for_valid_payload() {
        let request = post_request("/process/asteroid", valid_asteroid_json());

        let response = router().oneshot(request).await.unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn process_asteroid_returns_400_for_invalid_diameter() {
        let mut payload = valid_asteroid_json();
        payload["diameter_avg_km"] = serde_json::json!(-1.0);
        let request = post_request("/process/asteroid", payload);

        let response = router().oneshot(request).await.unwrap();

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn process_batch_rejects_empty_batch() {
        let request = post_request("/process/batch", serde_json::json!([]));

        let response = router().oneshot(request).await.unwrap();

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn process_batch_rejects_batch_over_500() {
        let batch: Vec<_> = (0..501)
            .map(|i| {
                let mut a = valid_asteroid_json();
                a["id"] = serde_json::json!(i.to_string());
                a
            })
            .collect();
        let request = post_request("/process/batch", serde_json::json!(batch));

        let response = router().oneshot(request).await.unwrap();

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn process_batch_skips_invalid_entries_but_processes_valid_ones() {
        let mut invalid = valid_asteroid_json();
        invalid["diameter_avg_km"] = serde_json::json!(-1.0);
        let batch = serde_json::json!([valid_asteroid_json(), invalid]);
        let request = post_request("/process/batch", batch);

        let response = router().oneshot(request).await.unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }
}
