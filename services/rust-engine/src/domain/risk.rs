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
        if score >= 75.0 {
            RiskLevel::Critical
        } else if score >= 50.0 {
            RiskLevel::High
        } else if score >= 25.0 {
            RiskLevel::Medium
        } else {
            RiskLevel::Low
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn boundaries_are_inclusive_on_their_lower_edge() {
        assert_eq!(RiskResult::compute_risk_level(75.0), RiskLevel::Critical);
        assert_eq!(RiskResult::compute_risk_level(50.0), RiskLevel::High);
        assert_eq!(RiskResult::compute_risk_level(25.0), RiskLevel::Medium);
        assert_eq!(RiskResult::compute_risk_level(0.0), RiskLevel::Low);
    }

    #[test]
    fn no_gap_just_below_each_boundary() {
        // Regression test: the old `match` used inclusive float ranges like
        // `50.0..=74.99`, leaving an uncovered gap between 74.99 and 75.0
        // (and between 49.99 and 50.0) that silently fell through to Low.
        assert_eq!(RiskResult::compute_risk_level(74.995), RiskLevel::High);
        assert_eq!(RiskResult::compute_risk_level(49.995), RiskLevel::Medium);
        assert_eq!(RiskResult::compute_risk_level(24.995), RiskLevel::Low);
    }

    #[test]
    fn top_and_bottom_of_range() {
        assert_eq!(RiskResult::compute_risk_level(100.0), RiskLevel::Critical);
        assert_eq!(RiskResult::compute_risk_level(24.99), RiskLevel::Low);
    }
}
