"""
Tests for app.core.dto_mapper — the boundary between raw, unpredictable
NASA API JSON and our internal Asteroid domain model.

This is high-value to test because NASA's data is not fully reliable
(missing fields, zero values, empty lists) and every skip-path here
protects the rest of the pipeline (Mongo, Rust Engine) from bad data.
"""
from app.core.dto_mapper import map_nasa_raw_to_asteroid, map_mongo_document_to_asteroid


def _valid_raw_asteroid(**overrides) -> dict:
    """A complete, well-formed NASA NeoWS asteroid record."""
    base = {
        "id": "2000433",
        "name": "433 Eros",
        "absolute_magnitude_h": 10.4,
        "estimated_diameter": {
            "kilometers": {
                "estimated_diameter_min": 22.0,
                "estimated_diameter_max": 25.0,
            }
        },
        "close_approach_data": [
            {
                "close_approach_date": "2025-01-01",
                "relative_velocity": {"kilometers_per_second": "5.5"},
                "miss_distance": {"kilometers": "26400000"},
                "orbiting_body": "Earth",
            }
        ],
        "is_potentially_hazardous_asteroid": False,
    }
    base.update(overrides)
    return base


class TestMapNasaRawToAsteroid:
    def test_valid_data_maps_all_fields_correctly(self):
        asteroid = map_nasa_raw_to_asteroid(_valid_raw_asteroid())

        assert asteroid is not None
        assert asteroid.id == "2000433"
        assert asteroid.name == "433 Eros"
        assert asteroid.diameter_km == 23.5  # (22.0 + 25.0) / 2
        assert asteroid.velocity_kps == 5.5
        assert asteroid.distance_km == 26_400_000.0
        assert asteroid.close_approach_date == "2025-01-01"
        assert asteroid.orbiting_body == "Earth"
        assert asteroid.is_potentially_hazardous is False

    def test_missing_id_is_rejected(self):
        raw = _valid_raw_asteroid()
        del raw["id"]

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_whitespace_only_id_is_rejected(self):
        raw = _valid_raw_asteroid(id="   ")

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_zero_diameter_is_rejected(self):
        raw = _valid_raw_asteroid(estimated_diameter={
            "kilometers": {"estimated_diameter_min": 0.0, "estimated_diameter_max": 0.0}
        })

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_missing_estimated_diameter_is_rejected(self):
        raw = _valid_raw_asteroid()
        del raw["estimated_diameter"]

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_empty_close_approach_data_is_rejected(self):
        raw = _valid_raw_asteroid(close_approach_data=[])

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_missing_close_approach_data_is_rejected(self):
        raw = _valid_raw_asteroid()
        del raw["close_approach_data"]

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_zero_velocity_is_rejected(self):
        raw = _valid_raw_asteroid(close_approach_data=[{
            "close_approach_date": "2025-01-01",
            "relative_velocity": {"kilometers_per_second": "0.0"},
            "miss_distance": {"kilometers": "26400000"},
            "orbiting_body": "Earth",
        }])

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_negative_velocity_is_rejected(self):
        # Shouldn't happen from NASA, but a negative velocity is as
        # non-physical as a zero one — the guard is `<= 0.0`.
        raw = _valid_raw_asteroid(close_approach_data=[{
            "close_approach_date": "2025-01-01",
            "relative_velocity": {"kilometers_per_second": "-5.0"},
            "miss_distance": {"kilometers": "26400000"},
            "orbiting_body": "Earth",
        }])

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_null_estimated_diameter_is_rejected_not_crashed(self):
        """Regression test: NASA sometimes sends `null` for a field instead
        of omitting it. `.get(key, {})` only falls back to `{}` when the
        key is *missing*, not when it's present but None — a naive
        `.get("estimated_diameter", {}).get("kilometers", {})` chain
        raises AttributeError on `None.get(...)`, which used to escape the
        `except (KeyError, ValueError, TypeError)` clause entirely and
        crash the whole batch pipeline over a single bad record."""
        raw = _valid_raw_asteroid(estimated_diameter=None)

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_null_close_approach_data_entry_is_rejected_not_crashed(self):
        raw = _valid_raw_asteroid(close_approach_data=[None])

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_null_id_is_rejected_not_crashed(self):
        raw = _valid_raw_asteroid(id=None)

        assert map_nasa_raw_to_asteroid(raw) is None

    def test_missing_optional_fields_fall_back_to_defaults(self):
        """NASA sometimes omits name/hazard flag/orbiting body; we should
        still produce a usable Asteroid rather than rejecting it."""
        raw = _valid_raw_asteroid()
        del raw["name"]
        del raw["is_potentially_hazardous_asteroid"]

        asteroid = map_nasa_raw_to_asteroid(raw)

        assert asteroid is not None
        assert asteroid.name == "Unknown"
        assert asteroid.is_potentially_hazardous is False


class TestMapMongoDocumentToAsteroid:
    def test_valid_document_maps_correctly(self):
        doc = {"asteroid": _valid_raw_asteroid()}

        asteroid = map_mongo_document_to_asteroid(doc)

        assert asteroid is not None
        assert asteroid.id == "2000433"

    def test_missing_asteroid_field_returns_none(self):
        assert map_mongo_document_to_asteroid({}) is None

    def test_empty_asteroid_field_returns_none(self):
        assert map_mongo_document_to_asteroid({"asteroid": {}}) is None
