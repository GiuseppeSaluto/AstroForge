"""
Tests for app.routes.nasa (the /nasa blueprint).

Mocks app.core.nasa_client at the call site (app.routes.nasa.*) rather than
its origin module — NASA's own HTTP behavior (retries, chunking) is already
covered in test_nasa_client.py. These tests cover the route's own job:
query param parsing/validation, response shaping, and HTTP status mapping
for upstream failures.
"""
from unittest.mock import MagicMock

import pytest
from flask import Flask
from requests.exceptions import HTTPError, RequestException

from app.routes.nasa import nasa_bp


def make_app(mongo=None) -> Flask:
    app = Flask(__name__)
    app.register_blueprint(nasa_bp)
    app.extensions = {"mongo": mongo} if mongo is not None else {}
    return app


def make_http_error(status_code: int) -> HTTPError:
    response = MagicMock()
    response.status_code = status_code
    return HTTPError(response=response)


def make_neo(id_, name, hazardous, diam_min, diam_max, velocity_kps, miss_km, approach_date="2025-01-01"):
    return {
        "id": id_,
        "neo_reference_id": id_,
        "name": name,
        "nasa_jpl_url": f"https://example.com/{id_}",
        "absolute_magnitude_h": 20.0,
        "is_potentially_hazardous_asteroid": hazardous,
        "estimated_diameter": {
            "kilometers": {"estimated_diameter_min": diam_min, "estimated_diameter_max": diam_max}
        },
        "close_approach_data": [{
            "close_approach_date": approach_date,
            "orbiting_body": "Earth",
            "relative_velocity": {"kilometers_per_second": str(velocity_kps)},
            "miss_distance": {"kilometers": str(miss_km), "lunar": "10.0"},
        }],
    }


@pytest.fixture
def client():
    return make_app().test_client()


class TestNeoFeed:
    def test_returns_nasa_feed_as_is(self, client, mocker):
        mocker.patch("app.routes.nasa.get_neo_feed", return_value={"element_count": 1})

        response = client.get("/nasa/neo/feed?start_date=2025-01-01&end_date=2025-01-02")

        assert response.status_code == 200
        assert response.get_json() == {"element_count": 1}

    def test_rate_limit_returns_429(self, client, mocker):
        mocker.patch("app.routes.nasa.get_neo_feed", side_effect=make_http_error(429))

        response = client.get("/nasa/neo/feed")

        assert response.status_code == 429

    def test_other_http_error_returns_502(self, client, mocker):
        mocker.patch("app.routes.nasa.get_neo_feed", side_effect=make_http_error(500))

        response = client.get("/nasa/neo/feed")

        assert response.status_code == 502

    def test_network_error_returns_503(self, client, mocker):
        mocker.patch("app.routes.nasa.get_neo_feed", side_effect=RequestException("down"))

        response = client.get("/nasa/neo/feed")

        assert response.status_code == 503

    def test_unexpected_error_returns_500(self, client, mocker):
        mocker.patch("app.routes.nasa.get_neo_feed", side_effect=KeyError("boom"))

        response = client.get("/nasa/neo/feed")

        assert response.status_code == 500


class TestSaveNeoData:
    def test_saves_new_and_skips_existing(self, mocker):
        mongo = MagicMock()
        mongo.save_raw_asteroid.side_effect = [True, False]
        client = make_app(mongo=mongo).test_client()
        feed = {"near_earth_objects": {"2025-01-01": [{"id": "1"}, {"id": "2"}]}}
        mocker.patch("app.routes.nasa.get_neo_feed", return_value=feed)

        response = client.post("/nasa/neo/save?start_date=2025-01-01&end_date=2025-01-01")

        assert response.status_code == 200
        assert response.get_json() == {"status": "success", "stored": 1, "skipped": 1}
        mongo.save_nasa_feed.assert_called_once()

    def test_invalid_feed_returns_502(self, mocker):
        client = make_app(mongo=MagicMock()).test_client()
        mocker.patch("app.routes.nasa.get_neo_feed", return_value={})

        response = client.post("/nasa/neo/save")

        assert response.status_code == 502

    def test_mongo_not_initialized_returns_500(self, mocker):
        client = make_app(mongo=None).test_client()
        mocker.patch("app.routes.nasa.get_neo_feed", return_value={"near_earth_objects": {}})

        response = client.post("/nasa/neo/save")

        assert response.status_code == 500

    def test_request_exception_returns_503(self, mocker):
        client = make_app(mongo=MagicMock()).test_client()
        mocker.patch("app.routes.nasa.get_neo_feed", side_effect=RequestException("down"))

        response = client.post("/nasa/neo/save")

        assert response.status_code == 503


class TestListAsteroids:
    def test_default_range_and_dedup_keeps_smallest_distance(self, client, mocker):
        feed = {
            "near_earth_objects": {
                "2025-01-01": [make_neo("1", "Alpha", False, 0.1, 0.3, 10.0, 500_000)],
                "2025-01-02": [make_neo("1", "Alpha", False, 0.1, 0.3, 10.0, 200_000)],
            }
        }
        mocker.patch("app.routes.nasa.get_neo_feed_chunked", return_value=feed)

        response = client.get("/nasa/asteroids")

        assert response.status_code == 200
        body = response.get_json()
        assert body["total"] == 1
        assert body["asteroids"][0]["miss_distance_km"] == 200_000.0

    def test_invalid_date_format_returns_400(self, client):
        response = client.get("/nasa/asteroids?start_date=not-a-date")
        assert response.status_code == 400

    def test_end_before_start_returns_400(self, client):
        response = client.get("/nasa/asteroids?start_date=2025-01-10&end_date=2025-01-01")
        assert response.status_code == 400

    def test_range_too_large_returns_400(self, client):
        response = client.get("/nasa/asteroids?start_date=2025-01-01&end_date=2027-01-01")
        assert response.status_code == 400

    def test_invalid_is_hazardous_returns_400(self, client):
        response = client.get("/nasa/asteroids?is_hazardous=maybe")
        assert response.status_code == 400

    def test_invalid_sort_by_returns_400(self, client):
        response = client.get("/nasa/asteroids?sort_by=danger")
        assert response.status_code == 400

    def test_invalid_order_returns_400(self, client):
        response = client.get("/nasa/asteroids?order=sideways")
        assert response.status_code == 400

    def test_filters_by_hazardous_flag(self, client, mocker):
        feed = {
            "near_earth_objects": {
                "2025-01-01": [
                    make_neo("1", "Alpha", True, 0.1, 0.3, 10.0, 100_000),
                    make_neo("2", "Beta", False, 0.1, 0.3, 10.0, 5_000_000),
                ],
            }
        }
        mocker.patch("app.routes.nasa.get_neo_feed_chunked", return_value=feed)

        response = client.get("/nasa/asteroids?is_hazardous=true")

        body = response.get_json()
        assert body["total"] == 1
        assert body["asteroids"][0]["id"] == "1"

    def test_sorts_by_name_descending(self, client, mocker):
        feed = {
            "near_earth_objects": {
                "2025-01-01": [
                    make_neo("1", "Alpha", False, 0.1, 0.3, 10.0, 100_000),
                    make_neo("2", "Beta", False, 0.1, 0.3, 10.0, 200_000),
                ],
            }
        }
        mocker.patch("app.routes.nasa.get_neo_feed_chunked", return_value=feed)

        response = client.get("/nasa/asteroids?sort_by=name&order=desc")

        names = [a["name"] for a in response.get_json()["asteroids"]]
        assert names == ["Beta", "Alpha"]

    def test_upstream_rate_limit_returns_429(self, client, mocker):
        mocker.patch("app.routes.nasa.get_neo_feed_chunked", side_effect=make_http_error(429))

        response = client.get("/nasa/asteroids")

        assert response.status_code == 429


class TestAsteroidDetail:
    def test_returns_mapped_detail(self, client, mocker):
        data = {
            "id": "1", "neo_reference_id": "1", "name": "Alpha",
            "nasa_jpl_url": "url", "absolute_magnitude_h": 20.0,
            "is_potentially_hazardous_asteroid": True, "is_sentry_object": False,
            "estimated_diameter": {
                "kilometers": {"estimated_diameter_min": 0.1, "estimated_diameter_max": 0.3},
                "meters": {"estimated_diameter_min": 100.0, "estimated_diameter_max": 300.0},
            },
            "close_approach_data": [{
                "close_approach_date": "2025-01-01", "close_approach_date_full": "2025-Jan-01",
                "relative_velocity": {"kilometers_per_second": "10.0", "kilometers_per_hour": "36000.0"},
                "miss_distance": {"kilometers": "100000.0", "lunar": "10.0"},
                "orbiting_body": "Earth",
            }],
            "orbital_data": {"orbit_id": "1", "eccentricity": "0.1"},
        }
        mocker.patch("app.routes.nasa.get_asteroid_detail", return_value=data)

        response = client.get("/nasa/asteroids/1")

        assert response.status_code == 200
        body = response.get_json()
        assert body["name"] == "Alpha"
        assert body["is_potentially_hazardous"] is True
        assert body["close_approach_data"][0]["velocity_kps"] == 10.0

    def test_not_found_returns_404(self, client, mocker):
        mocker.patch("app.routes.nasa.get_asteroid_detail", side_effect=make_http_error(404))

        response = client.get("/nasa/asteroids/unknown")

        assert response.status_code == 404
