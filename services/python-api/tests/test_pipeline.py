"""
Tests for app.core.pipeline.

Mocks Mongo, the Rust client, and dto_mapper to isolate pipeline.py's own
orchestration logic (stats bookkeeping across partial failures).
"""
from unittest.mock import MagicMock

import pytest
from flask import Flask
from requests.exceptions import RequestException

from app.core.pipeline import analyze_unprocessed_asteroids
from app.core.rust_client import BatchResult
from app.models.asteroid import Asteroid


def make_asteroid(asteroid_id: str) -> Asteroid:
    return Asteroid(
        id=asteroid_id,
        name=f"Asteroid {asteroid_id}",
        diameter_km=0.3,
        velocity_kps=10.0,
        distance_km=100_000.0,
        is_potentially_hazardous=False,
    )


def make_raw_doc(asteroid_id: str) -> dict:
    return {"asteroid": {"id": asteroid_id}}


@pytest.fixture
def mock_mongo():
    return MagicMock()


@pytest.fixture
def app_context(mock_mongo):
    """Pushes a bare Flask app context with `mongo` registered, matching
    what `get_mongo()` expects —
    without going through `create_app()`, which opens a real MongoDB
    connection via `MongoDBClient.init_app`."""
    app = Flask(__name__)
    app.extensions["mongo"] = mock_mongo
    with app.app_context():
        yield app


@pytest.fixture
def app_context_without_mongo():
    app = Flask(__name__)
    with app.app_context():
        yield app


class TestAnalyzeUnprocessedAsteroids:
    def test_raises_if_mongo_not_initialized(self, app_context_without_mongo):
        with pytest.raises(RuntimeError, match="MongoDB extension not initialized"):
            analyze_unprocessed_asteroids()

    def test_returns_zeroed_stats_when_no_raw_asteroids(self, app_context, mock_mongo):
        mock_mongo.get_unprocessed_asteroids.return_value = []

        stats = analyze_unprocessed_asteroids(limit=50)

        mock_mongo.get_unprocessed_asteroids.assert_called_once_with(limit=50)
        assert stats == {"total_fetched": 0, "processed": 0, "failed": 0, "skipped": 0}
        mock_mongo.save_analysis_result.assert_not_called()

    def test_skips_documents_that_fail_mapping(self, app_context, mock_mongo, mocker):
        mock_mongo.get_unprocessed_asteroids.return_value = [make_raw_doc("1"), make_raw_doc("2")]
        mocker.patch("app.core.pipeline.map_mongo_document_to_asteroid", return_value=None)

        stats = analyze_unprocessed_asteroids()

        assert stats == {"total_fetched": 2, "processed": 0, "failed": 0, "skipped": 2}
        mock_mongo.save_analysis_result.assert_not_called()

    def test_processes_and_saves_valid_asteroids(self, app_context, mock_mongo, mocker):
        mock_mongo.get_unprocessed_asteroids.return_value = [make_raw_doc("1"), make_raw_doc("2")]
        mocker.patch(
            "app.core.pipeline.map_mongo_document_to_asteroid",
            side_effect=[make_asteroid("1"), make_asteroid("2")],
        )
        batch_mock = mocker.patch(
            "app.core.pipeline.process_asteroid_batch_with_rust",
            return_value=BatchResult(
                results=[
                    {"asteroid_id": "1", "risk_level": "Low"},
                    {"asteroid_id": "2", "risk_level": "High"},
                ],
                errors=[],
            ),
        )

        stats = analyze_unprocessed_asteroids()

        batch_mock.assert_called_once()
        assert stats == {"total_fetched": 2, "processed": 2, "failed": 0, "skipped": 0}
        assert mock_mongo.save_analysis_result.call_count == 2

    def test_asteroid_rejected_by_rust_counts_as_skipped(self, app_context, mock_mongo, mocker):
        # The Rust Engine rejects an asteroid that fails its own validation
        # (e.g. non-physical diameter), reporting it in `errors`.
        mock_mongo.get_unprocessed_asteroids.return_value = [make_raw_doc("1"), make_raw_doc("2")]
        mocker.patch(
            "app.core.pipeline.map_mongo_document_to_asteroid",
            side_effect=[make_asteroid("1"), make_asteroid("2")],
        )
        mocker.patch(
            "app.core.pipeline.process_asteroid_batch_with_rust",
            return_value=BatchResult(
                results=[{"asteroid_id": "1", "risk_level": "Low"}],
                errors=[{"id": "2", "details": "Invalid diameter: -1 km (must be > 0)"}],
            ),
        )

        stats = analyze_unprocessed_asteroids()

        assert stats == {"total_fetched": 2, "processed": 1, "failed": 0, "skipped": 1}

    def test_rust_engine_failure_propagates_and_saves_nothing(self, app_context, mock_mongo, mocker):
        mock_mongo.get_unprocessed_asteroids.return_value = [make_raw_doc("1"), make_raw_doc("2")]
        mocker.patch(
            "app.core.pipeline.map_mongo_document_to_asteroid",
            side_effect=[make_asteroid("1"), make_asteroid("2")],
        )
        mocker.patch(
            "app.core.pipeline.process_asteroid_batch_with_rust",
            side_effect=RequestException("connection refused"),
        )

        with pytest.raises(RequestException):
            analyze_unprocessed_asteroids()

        mock_mongo.save_analysis_result.assert_not_called()

    def test_mongo_save_failure_for_one_asteroid_does_not_stop_the_others(self, app_context, mock_mongo, mocker):
        mock_mongo.get_unprocessed_asteroids.return_value = [make_raw_doc("1"), make_raw_doc("2")]
        mocker.patch(
            "app.core.pipeline.map_mongo_document_to_asteroid",
            side_effect=[make_asteroid("1"), make_asteroid("2")],
        )
        mocker.patch(
            "app.core.pipeline.process_asteroid_batch_with_rust",
            return_value=BatchResult(
                results=[
                    {"asteroid_id": "1", "risk_level": "Low"},
                    {"asteroid_id": "2", "risk_level": "High"},
                ],
                errors=[],
            ),
        )
        mock_mongo.save_analysis_result.side_effect = [RuntimeError("mongo write error"), None]

        stats = analyze_unprocessed_asteroids()

        assert stats == {"total_fetched": 2, "processed": 1, "failed": 1, "skipped": 0}
