use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize, Default)]
pub enum RiskLevel {
    #[default]
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskResult {
    pub asteroid_id: String,
    pub asteroid_name: String,
    pub impact_energy_joules: f64,
    pub impact_energy_megatons: f64,
    pub risk_level: RiskLevel,
    pub risk_score_0_to_100: f64,
    pub is_potentially_hazardous: bool,
    pub miss_distance_km: f64,
    pub velocity_kps: f64,
    pub diameter_km: f64,
}

impl RiskResult {
    pub fn compute_risk_level(score: f64) -> RiskLevel {
        match score {
            75.0..=100.0 => RiskLevel::Critical,
            50.0..=74.99 => RiskLevel::High,
            25.0..=49.99 => RiskLevel::Medium,
            _ => RiskLevel::Low,
        }
    }
}
