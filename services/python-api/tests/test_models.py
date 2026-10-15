"""
Tests for app.models.asteroid.Asteroid.
"""
from app.models.asteroid import Asteroid


def test_to_dto_dict_matches_rust_dto_fields():
    asteroid = Asteroid(
        id="1", name="Alpha", diameter_km=0.3, velocity_kps=10.0,
        distance_km=100_000.0, is_potentially_hazardous=True,
    )

    # Must match rust-engine/src/dto/asteroid_dto.rs field for field.
    assert asteroid.to_dto_dict() == {
        "id": "1", "name": "Alpha", "diameter_avg_km": 0.3,
        "relative_velocity_kps": 10.0, "miss_distance_km": 100_000.0,
        "is_potentially_hazardous": True,
    }
