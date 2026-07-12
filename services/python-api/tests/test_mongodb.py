"""
Tests for the aggregation-backed query methods on app.core.mongodb.MongoDBClient
(get_pipeline_stats, get_close_approaches, get_analyzed_asteroids).

These used to live inline in the orchestration routes, reaching into
mongo.db["..."] directly; routes/test_routes_orchestration.py now covers
only response shaping and status mapping, and this file covers the actual
Mongo query construction.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pymongo.errors import PyMongoError

from app.core.mongodb import MongoDBClient


@pytest.fixture
def client():
    c = MongoDBClient("mongodb://localhost:27017", "test_db")
    c.db = MagicMock()
    return c


@pytest.fixture
def client_without_db():
    return MongoDBClient("mongodb://localhost:27017", "test_db")


def _two_collections(client: MongoDBClient, raw=None, analyses=None):
    """mongo.db["name"] is a __getitem__ call — a bare MagicMock returns the
    same child mock for every call regardless of the argument, so without
    this the two collection names would resolve to the same mock and
    clobber each other's setup."""
    raw = raw or MagicMock()
    analyses = analyses or MagicMock()
    client.db.__getitem__.side_effect = lambda name: {
        "asteroids_raw": raw,
        "asteroid_analyses": analyses,
    }[name]
    return raw, analyses


class TestGetPipelineStats:
    def test_raises_if_db_not_initialized(self, client_without_db):
        with pytest.raises(RuntimeError, match="Database not initialized"):
            client_without_db.get_pipeline_stats()

    def test_computes_all_fields(self, client):
        raw, analyses = _two_collections(client)
        raw.aggregate.return_value = [{"unprocessed": 3}]
        last_run = {"analysis_timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc)}
        analyses.count_documents.side_effect = [5, 2, 10]  # analyzed_today, high_risks, total
        analyses.find_one.return_value = last_run

        stats = client.get_pipeline_stats()

        assert stats == {
            "unprocessed": 3,
            "analyzed_today": 5,
            "total_analyzed": 10,
            "high_risks": 2,
            "last_pipeline_run": last_run["analysis_timestamp"],
        }

    def test_unprocessed_is_zero_when_aggregate_returns_empty(self, client):
        raw, analyses = _two_collections(client)
        raw.aggregate.return_value = []
        analyses.count_documents.side_effect = [0, 0, 0]
        analyses.find_one.return_value = None

        stats = client.get_pipeline_stats()

        assert stats["unprocessed"] == 0
        assert stats["last_pipeline_run"] is None

    def test_pymongo_error_propagates(self, client):
        client.db.__getitem__.side_effect = PyMongoError("down")

        with pytest.raises(PyMongoError):
            client.get_pipeline_stats()


class TestGetCloseApproaches:
    def test_raises_if_db_not_initialized(self, client_without_db):
        with pytest.raises(RuntimeError, match="Database not initialized"):
            client_without_db.get_close_approaches()

    def test_returns_aggregation_results(self, client):
        raw = MagicMock()
        raw.aggregate.return_value = [{"name": "Alpha", "miss_km": 123.4}]
        client.db.__getitem__.return_value = raw

        results = client.get_close_approaches(limit=5)

        assert results == [{"name": "Alpha", "miss_km": 123.4}]
        pipeline = raw.aggregate.call_args[0][0]
        assert pipeline[-1] == {"$limit": 5}

    def test_pymongo_error_propagates(self, client):
        client.db.__getitem__.side_effect = PyMongoError("down")

        with pytest.raises(PyMongoError):
            client.get_close_approaches()


class TestGetAnalyzedAsteroids:
    def test_raises_if_db_not_initialized(self, client_without_db):
        with pytest.raises(RuntimeError, match="Database not initialized"):
            client_without_db.get_analyzed_asteroids(limit=10, sort_field="x", sort_dir=1)

    def test_applies_sort_and_limit(self, client):
        collection = MagicMock()
        collection.find.return_value.sort.return_value.limit.return_value = [{"id": "1"}]
        client.db.__getitem__.return_value = collection

        results = client.get_analyzed_asteroids(limit=50, sort_field="risk_data.risk_score_0_to_100", sort_dir=-1)

        assert results == [{"id": "1"}]
        collection.find.assert_called_once_with({}, {"_id": 0})
        collection.find.return_value.sort.assert_called_once_with("risk_data.risk_score_0_to_100", -1)
        collection.find.return_value.sort.return_value.limit.assert_called_once_with(50)

    def test_pymongo_error_propagates(self, client):
        client.db.__getitem__.side_effect = PyMongoError("down")

        with pytest.raises(PyMongoError):
            client.get_analyzed_asteroids(limit=10, sort_field="x", sort_dir=1)
