from dataclasses import dataclass

@dataclass
class Asteroid:
    id: str
    name: str
    absolute_magnitude_h: float
    diameter_km: float
    velocity_kps: float
    distance_km: float
    is_potentially_hazardous: bool
    close_approach_date: str
    orbiting_body: str

    def to_dto_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "absolute_magnitude_h": self.absolute_magnitude_h,
            "diameter_avg_km": self.diameter_km,
            "close_approach_date": self.close_approach_date,
            "relative_velocity_kps": self.velocity_kps,
            "miss_distance_km": self.distance_km,
            "orbiting_body": self.orbiting_body,
            "is_potentially_hazardous": self.is_potentially_hazardous,
        }
