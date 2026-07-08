"""
Tests for app.core.rust_client's HTTP response handling.

Covers the batch endpoint's actual wire format ({"results": [...], "errors":
[...]}), which pipeline.py's own mocks don't exercise since they patch the
function itself rather than the HTTP layer.
"""
import pytest
import requests

from app.core.config import RUST_ENGINE_URL
from app.core.rust_client import BatchResult, process_asteroid_batch_with_rust

BATCH_URL = f"{RUST_ENGINE_URL}/api/process/batch"


class TestProcessAsteroidBatchWithRust:
    def test_splits_response_into_results_and_errors(self, requests_mock):
        requests_mock.post(BATCH_URL, json={
            "results": [{"asteroid_id": "1", "risk_level": "Low"}],
            "errors": [{"id": "2", "details": "Invalid diameter: -1 km (must be > 0)"}],
        })

        batch = process_asteroid_batch_with_rust([{"id": "1"}, {"id": "2"}])

        assert isinstance(batch, BatchResult)
        assert batch.results == [{"asteroid_id": "1", "risk_level": "Low"}]
        assert batch.errors == [{"id": "2", "details": "Invalid diameter: -1 km (must be > 0)"}]

    def test_raises_on_invalid_json(self, requests_mock):
        requests_mock.post(BATCH_URL, text="not json")

        with pytest.raises(RuntimeError, match="invalid JSON"):
            process_asteroid_batch_with_rust([{"id": "1"}])

    def test_raises_on_http_error_status(self, requests_mock):
        requests_mock.post(BATCH_URL, status_code=500)

        with pytest.raises(requests.RequestException):
            process_asteroid_batch_with_rust([{"id": "1"}])
