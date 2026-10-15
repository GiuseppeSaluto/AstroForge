use std::f64::consts::PI;

// ponytail: one density for every NEO (silicaceous, the NEO default).
// Carbonaceous ~1300 and metallic ~5300 kg/m³ would need a per-asteroid
// type estimate first; reintroduce an enum only when that input exists.
const SILICACEOUS_DENSITY_KG_M3: f64 = 2700.0;

const LUNAR_DISTANCE_KM: f64 = 384_400.0;
/// NeoWS feed results reach ~0.5 AU ≈ 195 lunar distances (checked against
/// real data: 207 stored NEOs span 3.7–194 LD, median 116 LD).
const NEOWS_MAX_DISTANCE_LD: f64 = 195.0;
const MIN_PROXIMITY_FACTOR: f64 = 0.5;

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

    pub fn mass_from_volume(volume_m3: f64) -> f64 {
        volume_m3 * SILICACEOUS_DENSITY_KG_M3
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

    /// Scales the score down for distant passes, on a log scale over the
    /// distance range NeoWS actually returns: 1 LD → ×1.0, ~195 LD (0.5 AU,
    /// the far edge of the feed) → ×0.5. Log scale because going from 1 to
    /// 2 LD matters far more than going from 100 to 101 LD.
    ///
    /// The floor is 0.5, not lower, on purpose: distance modulates the
    /// score, it doesn't erase it. (The previous curve hit its 0.2 floor
    /// at ~17 LD, so 97% of real NeoWS passes got the same factor.)
    pub fn apply_proximity_factor(score: f64, miss_distance_km: f64) -> f64 {
        // `.max(1.0)`: log10 of anything below 1 is negative (and log10(0)
        // is -inf in f64, no panic), so passes inside 1 LD just get ×1.0.
        let distance_ld = (miss_distance_km / LUNAR_DISTANCE_KM).max(1.0);
        // 0.0 at 1 LD, 1.0 at the NeoWS far edge, >1.0 beyond it.
        let farness = distance_ld.log10() / NEOWS_MAX_DISTANCE_LD.log10();
        let factor = (1.0 - (1.0 - MIN_PROXIMITY_FACTOR) * farness).clamp(MIN_PROXIMITY_FACTOR, 1.0);
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
        // Inside 1 lunar distance (384,400 km) the factor is clamped to 1.0
        let score = 70.0;
        let result = ImpactPhysics::apply_proximity_factor(score, 200_000.0);
        assert_eq!(result, score);
    }

    #[test]
    fn proximity_output_stays_in_range() {
        for dist in [0.0, 500_000.0, 3_000_000.0, 75_000_000.0, 1e12] {
            let result = ImpactPhysics::apply_proximity_factor(80.0, dist);
            assert!(
                (0.0..=100.0).contains(&result),
                "Out of range at dist={dist}: {result}"
            );
        }
    }

    #[test]
    fn far_edge_of_neows_range_halves_the_score() {
        // 195 LD ≈ 75,000,000 km is the far edge of the feed → ×0.5,
        // and anything beyond it stays at the 0.5 floor.
        let at_edge = ImpactPhysics::apply_proximity_factor(80.0, 195.0 * LUNAR_DISTANCE_KM);
        let beyond = ImpactPhysics::apply_proximity_factor(80.0, 1e12);
        assert!((at_edge - 40.0).abs() < 1e-9, "got {at_edge}");
        assert!((beyond - 40.0).abs() < 1e-9, "got {beyond}");
    }

    #[test]
    fn typical_neows_distances_are_not_flattened_to_one_value() {
        // Regression: the old curve gave ×0.2 to every pass beyond ~17 LD,
        // i.e. 97% of real data. Typical passes (30 vs 150 LD) must now differ.
        let at_30_ld = ImpactPhysics::apply_proximity_factor(80.0, 30.0 * LUNAR_DISTANCE_KM);
        let at_150_ld = ImpactPhysics::apply_proximity_factor(80.0, 150.0 * LUNAR_DISTANCE_KM);
        assert!(at_30_ld - at_150_ld > 5.0, "30 LD={at_30_ld:.1}, 150 LD={at_150_ld:.1}");
    }

    #[test]
    fn large_close_hazardous_neo_scores_high() {
        // Real record from the DB: 152637 (1997 NC1), ~1.15 km, 8.89 km/s,
        // 2,565,838 km (~6.7 LD), flagged hazardous. Under the old curve it
        // scored 40 (Medium) — a km-scale PHA passing at 7 LD should be High.
        let ke = kinetic_energy_for(1.1469, 8.89);
        let score = ImpactPhysics::risk_score_from_energy(ke);
        let score = ImpactPhysics::apply_proximity_factor(score, 2_565_838.0);
        let score = ImpactPhysics::apply_hazardous_bonus(score, true);
        assert!((50.0..75.0).contains(&score), "1997 NC1 should be High, got {score:.1}");
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
        let mass = ImpactPhysics::mass_from_volume(vol);
        ImpactPhysics::kinetic_energy_joules(mass, velocity_kps)
    }
}
