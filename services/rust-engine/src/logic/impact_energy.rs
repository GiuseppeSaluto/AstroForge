use std::f64::consts::PI;

#[derive(Debug, Clone, Copy)]
pub enum AsteroidDensity {
    CType, // Carbonaceous
    SType, // Silicaceous
    MType, // Metallic
}

impl AsteroidDensity {
    pub fn as_value(&self) -> f64 {
        match self {
            AsteroidDensity::CType => 1300.0,
            AsteroidDensity::SType => 2700.0, // (NEO default)
            AsteroidDensity::MType => 5300.0,
        }
    }
}

/// Physical calculations based on diameter (km) and velocity (km/s)
pub struct ImpactPhysics;

impl ImpactPhysics {
    /// kilometers to meters.
    #[inline]
    fn km_to_m(value: f64) -> f64 {
        value * 1000.0
    }

    /// Computes asteroid volume assuming spherical shape.
    pub fn volume_from_diameter_km(diameter_km: f64) -> f64 {
        let r_m = Self::km_to_m(diameter_km) / 2.0;
        (4.0 / 3.0) * PI * r_m.powi(3)
    }

    /// Computes mass = volume * density.
    pub fn mass_from_volume(volume_m3: f64, density: AsteroidDensity) -> f64 {
        volume_m3 * density.as_value()
    }

    /// Computes kinetic energy E = 1/2 m v²
    pub fn kinetic_energy_joules(mass_kg: f64, velocity_kps: f64) -> f64 {
        let v_mps = Self::km_to_m(velocity_kps);
        0.5 * mass_kg * v_mps.powi(2)
    }

    /// Converts joules to megatons of TNT equivalent.
    pub fn joules_to_megatons(joules: f64) -> f64 {
        joules / 4.184e15
    }

    /// Produces a 0–100 risk score based on impact energy.
    /// Uses a logarithmic scale to avoid exploding values.
    pub fn risk_score_from_energy(energy_joules: f64) -> f64 {
        if energy_joules <= 0.0 {
            return 0.0;
        }

        // Logarithmic scaling for human-readable risk metrics.
        let log_energy = (energy_joules.log10()).max(0.0);

        // Normalize: 15 = ~1 megaton, 20 = ~100 megatons, etc.
        let normalized = (log_energy / 20.0) * 100.0;

        normalized.clamp(0.0, 100.0)
    }
}
