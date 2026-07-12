"""
Tests for app.core.ingestion.IngestionPipeline.

Mocks Mongo and app.core.nasa_client.get_neo_feed to isolate ingestion.py's
own orchestration logic (dedup bookkeeping, feed-log fields).
"""
from unittest.mock import MagicMock

import pytest
from flask import Flask

from app.core.ingestion import IngestionPipeline


@pytest.fixture
def mock_mongo():
    return MagicMock()


@pytest.fixture
def app_context(mock_mongo):
    app = Flask(__name__)
    app.extensions["mongo"] = mock_mongo
    with app.app_context():
        yield app


@pytest.fixture
def app_context_without_mongo():
    app = Flask(__name__)
    with app.app_context():
        yield app


class TestIngestNeoFeed:
    def test_raises_if_mongo_not_initialized(self, app_context_without_mongo):
        with pytest.raises(RuntimeError, match="MongoDB extension not initialized"):
            IngestionPipeline.ingest_neo_feed()

    def test_raises_value_error_on_invalid_feed(self, app_context, mocker):
        mocker.patch("app.core.ingestion.get_neo_feed", return_value={})

        with pytest.raises(ValueError, match="Invalid feed from NASA"):
            IngestionPipeline.ingest_neo_feed()

    def test_saves_new_and_skips_existing(self, app_context, mock_mongo, mocker):
        feed = {"near_earth_objects": {"2025-01-01": [{"id": "1"}, {"id": "2"}]}}
        mocker.patch("app.core.ingestion.get_neo_feed", return_value=feed)
        mock_mongo.save_raw_asteroid.side_effect = [True, False]

        result = IngestionPipeline.ingest_neo_feed(start_date="2025-01-01", end_date="2025-01-01")

        assert result == {"saved": 1, "skipped": 1, "total_in_feed": 2}

    def test_logs_feed_with_resolved_date_range(self, app_context, mock_mongo, mocker):
        feed = {
            "near_earth_objects": {
                "2025-01-02": [{"id": "1"}],
                "2025-01-01": [{"id": "2"}],
            }
        }
        mocker.patch("app.core.ingestion.get_neo_feed", return_value=feed)
        mock_mongo.save_raw_asteroid.return_value = True

        IngestionPipeline.ingest_neo_feed(start_date=None, end_date=None)

        mock_mongo.save_nasa_feed.assert_called_once()
        logged = mock_mongo.save_nasa_feed.call_args[0][0]
        assert logged["feed_start_date"] == "2025-01-01"
        assert logged["feed_end_date"] == "2025-01-02"
        assert logged["saved"] == 2
        assert logged["skipped"] == 0
        assert logged["total_in_feed"] == 2
        assert "retrieved_at" in logged

    def test_falls_back_to_request_dates_when_feed_is_empty(self, app_context, mock_mongo, mocker):
        mocker.patch("app.core.ingestion.get_neo_feed", return_value={"near_earth_objects": {}})

        result = IngestionPipeline.ingest_neo_feed(start_date="2025-01-01", end_date="2025-01-07")

        assert result == {"saved": 0, "skipped": 0, "total_in_feed": 0}
        logged = mock_mongo.save_nasa_feed.call_args[0][0]
        assert logged["feed_start_date"] == "2025-01-01"
        assert logged["feed_end_date"] == "2025-01-07"
