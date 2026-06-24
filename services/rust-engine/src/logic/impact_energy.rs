use std::f64::consts::PI;

// Kept for future density differentiation (e.g. using absolute_magnitude_h as proxy).
#[allow(dead_code)]
#[derive(Debug, Clone, Copy)]
pub enum AsteroidDensity {
    CType, // Carbonaceous  ~1300 kg/m³
    SType, // Silicaceous   ~2700 kg/m³  (NEO default)
    MType, // Metallic      ~5300 kg/m³
}

impl AsteroidDensity {
    pub fn as_value(&self) -> f64 {
        match self {
            AsteroidDensity::CType => 1300.0,
            AsteroidDensity::SType => 2700.0,
            AsteroidDensity::MType => 5300.0,
        }
    }
}

pub struct ImpactPhysics;

impl ImpactPhysics {
    #[inline]
    fn km_to_m(value: f64) -> f64 {
        value * 1000.0
    }

    pub fn volume_from_diameter_km(diameter_km: f64) -> f64 {
        let r_m = Self::km_to_m(diameter_km) / 2.0;
        (4.0 / 3.0) * PI * r_m.powi(3)
    }

    pub fn mass_from_volume(volume_m3: f64, density: AsteroidDensity) -> f64 {
        volume_m3 * density.as_value()
    }

    pub fn kinetic_energy_joules(mass_kg: f64, velocity_kps: f64) -> f64 {
        let v_mps = Self::km_to_m(velocity_kps);
        0.5 * mass_kg * v_mps.powi(2)
    }

    pub fn joules_to_megatons(joules: f64) -> f64 {
        joules / 4.184e15
    }

    /// Base risk score 0–100 from impact energy alone.
    ///
    /// Calibrated on real events:
    ///   ~10^15 J  (Chelyabinsk, 17 m)  → ~27  Medium
    ///   ~10^16 J  (Tunguska, 50 m)     → ~36  Medium
    ///   ~10^18 J  (city-killer, 200 m) → ~55  High
    ///   ~10^20 J  (global, 1 km)       → ~73  High/Critical boundary
    pub fn risk_score_from_energy(energy_joules: f64) -> f64 {
        if energy_joules <= 0.0 {
            return 0.0;
        }
        let log_energy = energy_joules.log10();
        let normalized = (log_energy - 12.0) / 11.0 * 100.0;
        normalized.clamp(0.0, 100.0)
    }

    /// Reduces the score for asteroids with large miss distances.
    ///
    /// NASA NeoWS tracks objects within ~7,500,000 km (0.05 AU).
    /// Objects passing within 500,000 km receive the full score.
    /// At 7,500,000 km the factor bottoms out at 0.2.
    pub fn apply_proximity_factor(score: f64, miss_distance_km: f64) -> f64 {
        let factor = (1_500_000.0 / (miss_distance_km + 1_000_000.0)).clamp(0.2, 1.0);
        (score * factor).clamp(0.0, 100.0)
    }

    /// Adds a flat +10 bonus when NASA has flagged the asteroid as potentially
    /// hazardous. NASA's PHO classification already accounts for orbital
    /// mechanics (MOID < 0.05 AU and diameter > 140 m), so we treat it as
    /// independent confirmed evidence of danger.
    pub fn apply_hazardous_bonus(score: f64, is_hazardous: bool) -> f64 {
        if is_hazardous {
            (score + 10.0).clamp(0.0, 100.0)
        } else {
            score
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── risk_score_from_energy ────────────────────────────────────────────────

    #[test]
    fn zero_energy_returns_zero() {
        assert_eq!(ImpactPhysics::risk_score_from_energy(0.0), 0.0);
    }

    #[test]
    fn negative_energy_returns_zero() {
        assert_eq!(ImpactPhysics::risk_score_from_energy(-1.0), 0.0);
    }

    #[test]
    fn score_is_clamped_to_100() {
        assert_eq!(ImpactPhysics::risk_score_from_energy(f64::MAX), 100.0);
    }

    #[test]
    fn chelyabinsk_scores_medium() {
        // 17 m diameter, 18 km/s — the 2013 Chelyabinsk event
        let ke = kinetic_energy_for(0.017, 18.0);
        let score = ImpactPhysics::risk_score_from_energy(ke);
        assert!(
            (25.0..50.0).contains(&score),
            "Chelyabinsk should be Medium, got {score:.1}"
        );
    }

    #[test]
    fn tunguska_scores_medium() {
        // 50 m diameter, 15 km/s — the 1908 Tunguska event
        let ke = kinetic_energy_for(0.050, 15.0);
        let score = ImpactPhysics::risk_score_from_energy(ke);
        assert!(
            (25.0..50.0).contains(&score),
            "Tunguska should be Medium, got {score:.1}"
        );
    }

    #[test]
    fn city_killer_scores_high() {
        // 200 m diameter, 20 km/s
        let ke = kinetic_energy_for(0.200, 20.0);
        let score = ImpactPhysics::risk_score_from_energy(ke);
        assert!(
            (50.0..75.0).contains(&score),
            "City-killer should be High, got {score:.1}"
        );
    }

    #[test]
    fn km_scale_scores_critical() {
        // 1 km diameter, 20 km/s
        let ke = kinetic_energy_for(1.0, 20.0);
        let score = ImpactPhysics::risk_score_from_energy(ke);
        assert!(score >= 75.0, "1 km asteroid should be Critical, got {score:.1}");
    }

    // ── apply_proximity_factor ────────────────────────────────────────────────

    #[test]
    fn close_pass_scores_higher_than_far_pass() {
        let base = 60.0;
        let close = ImpactPhysics::apply_proximity_factor(base, 100_000.0);
        let far = ImpactPhysics::apply_proximity_factor(base, 6_000_000.0);
        assert!(close > far, "close={close:.1} should exceed far={far:.1}");
    }

    #[test]
    fn very_close_pass_preserves_full_score() {
        // Within 500,000 km factor is clamped to 1.0
        let score = 70.0;
        let result = ImpactPhysics::apply_proximity_factor(score, 200_000.0);
        assert_eq!(result, score);
    }

    #[test]
    fn proximity_output_stays_in_range() {
        for dist in [0.0, 500_000.0, 3_000_000.0, 7_500_000.0] {
            let result = ImpactPhysics::apply_proximity_factor(80.0, dist);
            assert!(
                (0.0..=100.0).contains(&result),
                "Out of range at dist={dist}: {result}"
            );
        }
    }

    // ── apply_hazardous_bonus ─────────────────────────────────────────────────

    #[test]
    fn hazardous_flag_increases_score() {
        let base = 50.0;
        let boosted = ImpactPhysics::apply_hazardous_bonus(base, true);
        let plain = ImpactPhysics::apply_hazardous_bonus(base, false);
        assert!(boosted > plain);
    }

    #[test]
    fn non_hazardous_score_unchanged() {
        let score = 42.0;
        assert_eq!(ImpactPhysics::apply_hazardous_bonus(score, false), score);
    }

    #[test]
    fn hazardous_bonus_clamped_to_100() {
        assert_eq!(ImpactPhysics::apply_hazardous_bonus(95.0, true), 100.0);
    }

    // ── helper ────────────────────────────────────────────────────────────────

    fn kinetic_energy_for(diameter_km: f64, velocity_kps: f64) -> f64 {
        let vol = ImpactPhysics::volume_from_diameter_km(diameter_km);
        let mass = ImpactPhysics::mass_from_volume(vol, AsteroidDensity::SType);
        ImpactPhysics::kinetic_energy_joules(mass, velocity_kps)
    }
}
