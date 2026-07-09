"""
Tests for app.models.asteroid.Asteroid.
"""
from app.models.asteroid import Asteroid


def test_to_dto_dict_maps_all_fields():
    asteroid = Asteroid(
        id="1", name="Alpha", absolute_magnitude_h=20.0, diameter_km=0.3,
        velocity_kps=10.0, distance_km=100_000.0, is_potentially_hazardous=True,
        close_approach_date="2025-01-01", orbiting_body="Earth",
    )

    assert asteroid.to_dto_dict() == {
        "id": "1", "name": "Alpha", "absolute_magnitude_h": 20.0,
        "diameter_min_km": 0.3, "diameter_max_km": 0.3, "diameter_avg_km": 0.3,
        "close_approach_date": "2025-01-01", "relative_velocity_kps": 10.0,
        "miss_distance_km": 100_000.0, "orbiting_body": "Earth",
        "is_potentially_hazardous": True,
    }
