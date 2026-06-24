use crate::{domain::error::DomainError, dto::asteroid_dto::AsteroidDTO};

#[derive(Debug, Clone)]
pub struct Asteroid {
    pub id: String,
    pub name: String,
    pub diameter_km: f64,
    pub velocity_kps: f64,
    pub distance_km: f64,
    pub hazardous: bool,
}

impl TryFrom<AsteroidDTO> for Asteroid {
    type Error = DomainError;

    fn try_from(dto: AsteroidDTO) -> Result<Self, Self::Error> {
        if dto.id.trim().is_empty() {
            return Err(DomainError::InvalidId);
        }
        if dto.diameter_avg_km <= 0.0 {
            return Err(DomainError::InvalidDiameter(dto.diameter_avg_km));
        }
        if dto.relative_velocity_kps < 0.0 {
            return Err(DomainError::InvalidVelocity(dto.relative_velocity_kps));
        }
        if dto.miss_distance_km < 0.0 {
            return Err(DomainError::InvalidField("miss_distance_km"));
        }

        Ok(Asteroid {
            id: dto.id,
            name: dto.name,
            diameter_km: dto.diameter_avg_km,
            velocity_kps: dto.relative_velocity_kps,
            distance_km: dto.miss_distance_km,
            hazardous: dto.is_potentially_hazardous,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::error::DomainError;
    use crate::dto::asteroid_dto::AsteroidDTO;

    fn valid_dto() -> AsteroidDTO {
        AsteroidDTO {
            id: "12345".to_string(),
            name: "Test Asteroid".to_string(),
            absolute_magnitude_h: 20.0,
            diameter_min_km: 0.1,
            diameter_max_km: 0.5,
            diameter_avg_km: 0.3,
            close_approach_date: "2025-01-01".to_string(),
            relative_velocity_kps: 10.0,
            miss_distance_km: 100_000.0,
            orbiting_body: "Earth".to_string(),
            is_potentially_hazardous: false,
        }
    }

    #[test]
    fn valid_dto_converts_successfully() {
        assert!(Asteroid::try_from(valid_dto()).is_ok());
    }

    #[test]
    fn negative_diameter_is_rejected() {
        let mut dto = valid_dto();
        dto.diameter_avg_km = -0.25;
        match Asteroid::try_from(dto).unwrap_err() {
            DomainError::InvalidDiameter(v) => assert!(v < 0.0),
            other => panic!("Unexpected error: {other:?}"),
        }
    }

    #[test]
    fn negative_velocity_is_rejected() {
        let mut dto = valid_dto();
        dto.relative_velocity_kps = -5.0;
        match Asteroid::try_from(dto).unwrap_err() {
            DomainError::InvalidVelocity(v) => assert!(v < 0.0),
            other => panic!("Unexpected error: {other:?}"),
        }
    }

    #[test]
    fn empty_id_is_rejected() {
        let mut dto = valid_dto();
        dto.id = "   ".to_string();
        assert!(matches!(Asteroid::try_from(dto).unwrap_err(), DomainError::InvalidId));
    }
}
