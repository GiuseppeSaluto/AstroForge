use serde::{Deserialize, Serialize};

/// Wire format sent by the Python API — only the fields the risk model reads.
///
/// serde ignores unknown JSON fields by default (no `deny_unknown_fields`),
/// so a client still sending the old 11-field payload keeps working.
#[derive(Serialize, Deserialize)]
pub struct AsteroidDTO {
    pub id: String,
    pub name: String,
    pub diameter_avg_km: f64,
    pub relative_velocity_kps: f64,
    pub miss_distance_km: f64,
    pub is_potentially_hazardous: bool,
}
