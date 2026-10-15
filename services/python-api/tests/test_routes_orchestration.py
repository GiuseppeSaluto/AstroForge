"""
Tests for app.routes.orchestration (the /pipeline blueprint).

app.core.pipeline's own orchestration logic is covered in test_pipeline.py;
these tests cover the route layer's own job: query param validation,
Mongo aggregation result shaping, and HTTP status mapping.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import requests

from flask import Flask

from app.routes.orchestration import orchestration_bp
from app.utils.error_handlers import register_error_handlers


def make_app(mongo=None) -> Flask:
    app = Flask(__name__)
    app.register_blueprint(orchestration_bp)
    register_error_handlers(app)
    app.extensions = {"mongo": mongo} if mongo is not None else {}
    return app


class TestAnalyzeNeoPipeline:
    def test_runs_pipeline_and_returns_stats(self, mocker):
        stats = {"total_fetched": 2, "processed": 2, "failed": 0, "skipped": 0}
        mocker.patch(
            "app.routes.orchestration.analyze_unprocessed_asteroids",
            return_value=stats,
        )
        client = make_app().test_client()

        response = client.post("/pipeline/neo/analyze?limit=50")

        assert response.status_code == 200
        assert response.get_json() == {"status": "success", "statistics": stats}

    def test_limit_out_of_range_returns_400(self):
        client = make_app().test_client()

        response = client.post("/pipeline/neo/analyze?limit=0")

        assert response.status_code == 400


class TestAnalyzeNeoPipelineRustFailures:
    """Drives the real pipeline + rust_client (only Mongo and the HTTP layer
    are faked), so these check what the dashboard actually receives."""

    RAW_DOC = {"asteroid": {
        "id": "1", "name": "Alpha",
        "estimated_diameter": {"kilometers": {"estimated_diameter_min": 0.1, "estimated_diameter_max": 0.3}},
        "close_approach_data": [{
            "relative_velocity": {"kilometers_per_second": "10.0"},
            "miss_distance": {"kilometers": "100000.0"},
        }],
    }}

    def _client(self):
        mongo = MagicMock()
        mongo.get_unprocessed_asteroids.return_value = [self.RAW_DOC]
        return make_app(mongo=mongo).test_client(), mongo

    def test_missing_rust_engine_url_is_500(self, monkeypatch):
        # Regression (step 1): a missing URL used to surface as a 404.
        monkeypatch.setattr("app.core.rust_client.RUST_ENGINE_URL", None)
        client, _ = self._client()

        response = client.post("/pipeline/neo/analyze")

        assert response.status_code == 500
        assert "RUST_ENGINE_URL" in response.get_json()["details"]

    def test_unreachable_rust_engine_is_503_not_success(self, monkeypatch, requests_mock):
        # Regression: used to return 200 "success" with every asteroid
        # counted as failed, so the dashboard showed a green "0 processed".
        monkeypatch.setattr("app.core.rust_client.RUST_ENGINE_URL", "http://rust.test")
        requests_mock.post("http://rust.test/api/process/batch", exc=requests.ConnectionError("refused"))
        client, mongo = self._client()

        response = client.post("/pipeline/neo/analyze")

        assert response.status_code == 503
        assert response.get_json()["error"] == "Rust Engine unreachable"
        mongo.save_analysis_result.assert_not_called()


class TestPipelineStatus:
    def test_healthy_when_mongo_and_rust_ok(self, mocker):
        mongo = MagicMock()
        mocker.patch("app.routes.orchestration.check_rust_health", return_value="ok")
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/status")

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "healthy"
        assert body["components"]["rust_engine"] == "ok"

    def test_mongo_not_initialized_returns_503(self):
        client = make_app(mongo=None).test_client()

        response = client.get("/pipeline/status")

        assert response.status_code == 503

    def test_mongo_error_returns_503(self):
        mongo = MagicMock()
        mongo.ping.side_effect = RuntimeError("db down")
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/status")

        assert response.status_code == 503


class TestPipelineStats:
    """The Mongo aggregation itself is covered in test_mongodb.py; these
    tests cover the route's own job: response shaping and status mapping."""

    def _make_mongo(self, unprocessed=0, analyzed_today=0, high_risks=0, total=0, last_run=None):
        mongo = MagicMock()
        mongo.get_pipeline_stats.return_value = {
            "unprocessed": unprocessed,
            "analyzed_today": analyzed_today,
            "total_analyzed": total,
            "high_risks": high_risks,
            "last_pipeline_run": last_run,
        }
        return mongo

    def test_returns_computed_stats(self):
        last_run = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mongo = self._make_mongo(unprocessed=3, analyzed_today=5, high_risks=2, total=10, last_run=last_run)
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/stats")

        assert response.status_code == 200
        body = response.get_json()
        assert body["unprocessed"] == 3
        assert body["analyzed_today"] == 5
        assert body["high_risks"] == 2
        assert body["total_analyzed"] == 10
        assert body["last_pipeline_run"] == "2025-01-01T00:00:00+00:00"

    def test_no_last_run_is_null(self):
        mongo = self._make_mongo()
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/stats")

        assert response.get_json()["last_pipeline_run"] is None

    def test_mongo_not_initialized_returns_500(self):
        client = make_app(mongo=None).test_client()

        response = client.get("/pipeline/stats")

        assert response.status_code == 500

    def test_aggregation_error_returns_500(self):
        # stats no longer wraps this in a local try/except — checks the
        # error actually reaches the global RuntimeError handler.
        mongo = MagicMock()
        mongo.get_pipeline_stats.side_effect = RuntimeError("mongo down")
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/stats")

        assert response.status_code == 500
        assert response.get_json()["error"] == "Pipeline error"


class TestCloseApproaches:
    def test_returns_mapped_results_with_defaults(self):
        mongo = MagicMock()
        mongo.get_close_approaches.return_value = [
            {
                "name": "Alpha", "is_hazardous": True, "close_approach_date": "2025-01-01",
                "miss_km": 123.4, "velocity_kps": 10.5, "risk_level": "Low",
                "risk_score": 12.3, "diameter_km": 0.2,
            },
            {},
        ]
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/close-approaches?limit=5")

        assert response.status_code == 200
        body = response.get_json()
        assert body[0]["name"] == "Alpha"
        assert body[1] == {
            "name": "?", "is_hazardous": False, "close_approach_date": "",
            "miss_km": 0, "velocity_kps": 0.0, "risk_level": "Unknown",
            "risk_score": 0.0, "diameter_km": 0.0,
        }
        mongo.get_close_approaches.assert_called_once_with(limit=5)

    def test_mongo_not_initialized_returns_500(self):
        client = make_app(mongo=None).test_client()

        response = client.get("/pipeline/close-approaches")

        assert response.status_code == 500

    def test_aggregation_error_returns_500(self):
        mongo = MagicMock()
        mongo.get_close_approaches.side_effect = RuntimeError("mongo down")
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/close-approaches")

        assert response.status_code == 500
        assert response.get_json()["error"] == "Pipeline error"


class TestListAnalyzedAsteroids:
    def test_returns_mapped_results(self):
        mongo = MagicMock()
        doc = {
            "neo_reference_id": "1",
            "risk_data": {
                "asteroid_name": "Alpha", "risk_level": "Low", "risk_score_0_to_100": 12.3,
                "impact_energy_megatons": 0.001, "miss_distance_km": 100_000.0,
                "diameter_km": 0.2, "velocity_kps": 10.0, "is_potentially_hazardous": False,
            },
            "analysis_timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
        }
        mongo.get_analyzed_asteroids.return_value = [doc]
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/analysis/asteroids?sort=energy&order=asc")

        assert response.status_code == 200
        body = response.get_json()
        assert body[0]["id"] == "1"
        assert body[0]["name"] == "Alpha"
        mongo.get_analyzed_asteroids.assert_called_once_with(
            limit=200, sort_field="risk_data.impact_energy_megatons", sort_dir=1
        )

    def test_mongo_not_initialized_returns_500(self):
        client = make_app(mongo=None).test_client()

        response = client.get("/pipeline/analysis/asteroids")

        assert response.status_code == 500

    def test_query_error_returns_500(self):
        mongo = MagicMock()
        mongo.get_analyzed_asteroids.side_effect = RuntimeError("mongo down")
        client = make_app(mongo=mongo).test_client()

        response = client.get("/pipeline/analysis/asteroids")

        assert response.status_code == 500
        assert response.get_json()["error"] == "Pipeline error"
