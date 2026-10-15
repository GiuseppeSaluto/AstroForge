from dataclasses import dataclass

@dataclass
class Asteroid:
    """The subset of a NASA NEO record the Rust risk model actually uses."""
    id: str
    name: str
    diameter_km: float
    velocity_kps: float
    distance_km: float
    is_potentially_hazardous: bool

    def to_dto_dict(self) -> dict:
        """Wire format for the Rust Engine's AsteroidDTO (rust-engine/src/dto)."""
        return {
            "id": self.id,
            "name": self.name,
            "diameter_avg_km": self.diameter_km,
            "relative_velocity_kps": self.velocity_kps,
            "miss_distance_km": self.distance_km,
            "is_potentially_hazardous": self.is_potentially_hazardous,
        }
