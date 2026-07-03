"""
Tests for app.core.nasa_client.

Two behaviors here carry real production risk and are the focus of this
file:

1. `_get_with_retry` — NASA's public API key has a low hourly rate limit,
   so hitting 429 is a realistic occurrence, not a hypothetical. If the
   backoff logic is broken (wrong status code, wrong retry count, doesn't
   raise after exhausting retries), the whole pipeline silently misbehaves
   under load.
2. `get_neo_feed_chunked` — NASA's feed endpoint hard-caps windows at 7
   days (see CLAUDE.md); this function is what lets the rest of the app
   ask for arbitrary ranges. Off-by-one errors in the chunk boundaries
   would silently duplicate or drop asteroids for a given day, with no
   crash to reveal it.

Note: `_get_with_retry` starts with an underscore (Python's "internal use"
convention), but nothing stops us importing it directly in a test — unlike
Rust's `pub`/private visibility, this is enforced by convention only, not
by the interpreter.
"""
import pytest
import requests
from datetime import date

from app.core.config import NASA_BASE_URL, NASA_NEO_FEED_ENDPOINT
from app.core.cache import cache_clear
from app.core.nasa_client import _get_with_retry, get_neo_feed, get_neo_feed_chunked

FEED_URL = f"{NASA_BASE_URL}{NASA_NEO_FEED_ENDPOINT}"


@pytest.fixture(autouse=True)
def clear_cache():
    """nasa_client caches results in a process-wide TTLCache (app/core/cache.py).
    Without clearing it, a cache hit left over from an earlier test would
    silently skip the mocked HTTP call in a later one, hiding real bugs
    (or a stale value from a numerically-clashing date range: "cache
    poisoning" across tests, in effect)."""
    cache_clear()
    yield
    cache_clear()


class TestGetWithRetry:
    def test_succeeds_on_first_try_without_sleeping(self, requests_mock, mocker):
        sleep = mocker.patch("app.core.nasa_client.time.sleep")
        requests_mock.get(FEED_URL, json={"ok": True}, status_code=200)

        response = _get_with_retry(FEED_URL, {})

        assert response.status_code == 200
        assert requests_mock.call_count == 1
        sleep.assert_not_called()

    def test_retries_on_429_then_succeeds(self, requests_mock, mocker):
        sleep = mocker.patch("app.core.nasa_client.time.sleep")
        requests_mock.get(FEED_URL, [
            {"status_code": 429},
            {"json": {"ok": True}, "status_code": 200},
        ])

        response = _get_with_retry(FEED_URL, {})

        assert response.status_code == 200
        assert requests_mock.call_count == 2
        sleep.assert_called_once_with(1)  # 2 ** 0

    def test_raises_after_exhausting_all_retries(self, requests_mock, mocker):
        mocker.patch("app.core.nasa_client.time.sleep")
        requests_mock.get(FEED_URL, status_code=429)

        with pytest.raises(requests.exceptions.HTTPError, match="rate limit exceeded"):
            _get_with_retry(FEED_URL, {}, max_retries=3)

        assert requests_mock.call_count == 3

    def test_does_not_retry_on_non_429_error(self, requests_mock, mocker):
        sleep = mocker.patch("app.core.nasa_client.time.sleep")
        requests_mock.get(FEED_URL, status_code=500)

        with pytest.raises(requests.exceptions.HTTPError):
            _get_with_retry(FEED_URL, {})

        # A 500 isn't a rate limit — it should fail immediately, not
        # consume the retry budget meant for 429s.
        assert requests_mock.call_count == 1
        sleep.assert_not_called()


class TestGetNeoFeed:
    def test_defaults_to_a_7_day_window_starting_today(self, requests_mock):
        requests_mock.get(FEED_URL, json={"element_count": 0, "near_earth_objects": {}})

        get_neo_feed()

        qs = requests_mock.last_request.qs
        start = date.fromisoformat(qs["start_date"][0])
        end = date.fromisoformat(qs["end_date"][0])
        assert start == date.today()
        assert (end - start).days == 6  # 7-day window is inclusive of both ends

    def test_caches_result_and_skips_second_http_call(self, requests_mock):
        requests_mock.get(FEED_URL, json={"element_count": 0, "near_earth_objects": {}})

        get_neo_feed(start_date="2025-01-01", end_date="2025-01-07")
        get_neo_feed(start_date="2025-01-01", end_date="2025-01-07")

        assert requests_mock.call_count == 1


class TestGetNeoFeedChunked:
    def test_range_of_exactly_7_days_makes_a_single_request(self, requests_mock):
        requests_mock.get(FEED_URL, json={
            "element_count": 2,
            "near_earth_objects": {"2025-01-01": [{"id": "1"}, {"id": "2"}]},
        })

        result = get_neo_feed_chunked("2025-01-01", "2025-01-07")

        assert requests_mock.call_count == 1
        assert result["element_count"] == 2

    def test_range_over_7_days_splits_into_correctly_bounded_chunks(self, requests_mock):
        requests_mock.get(FEED_URL, [
            {"json": {"element_count": 1, "near_earth_objects": {"2025-01-01": [{"id": "a"}]}}},
            {"json": {"element_count": 1, "near_earth_objects": {"2025-01-08": [{"id": "b"}]}}},
        ])

        get_neo_feed_chunked("2025-01-01", "2025-01-10")

        assert requests_mock.call_count == 2
        first_call, second_call = requests_mock.request_history
        # No gap and no overlap: chunk 2 must pick up exactly where chunk 1 left off.
        assert first_call.qs["start_date"] == ["2025-01-01"]
        assert first_call.qs["end_date"] == ["2025-01-07"]
        assert second_call.qs["start_date"] == ["2025-01-08"]
        assert second_call.qs["end_date"] == ["2025-01-10"]

    def test_range_that_is_an_exact_multiple_of_7_has_no_gap_or_overlap(self, requests_mock):
        # 14-day range = exactly two full 7-day chunks; the boundary is
        # the easiest place for an off-by-one to hide.
        requests_mock.get(FEED_URL, [
            {"json": {"element_count": 0, "near_earth_objects": {}}},
            {"json": {"element_count": 0, "near_earth_objects": {}}},
        ])

        get_neo_feed_chunked("2025-01-01", "2025-01-14")

        assert requests_mock.call_count == 2
        first_call, second_call = requests_mock.request_history
        assert first_call.qs["end_date"] == ["2025-01-07"]
        assert second_call.qs["start_date"] == ["2025-01-08"]
        assert second_call.qs["end_date"] == ["2025-01-14"]

    def test_single_day_range_makes_exactly_one_request(self, requests_mock):
        requests_mock.get(FEED_URL, json={"element_count": 0, "near_earth_objects": {}})

        get_neo_feed_chunked("2025-01-01", "2025-01-01")

        assert requests_mock.call_count == 1
        assert requests_mock.last_request.qs["start_date"] == ["2025-01-01"]
        assert requests_mock.last_request.qs["end_date"] == ["2025-01-01"]

    def test_aggregates_asteroids_from_all_chunks_without_losing_any(self, requests_mock):
        requests_mock.get(FEED_URL, [
            {"json": {"element_count": 1, "near_earth_objects": {"2025-01-01": [{"id": "a"}]}}},
            {"json": {"element_count": 2, "near_earth_objects": {"2025-01-08": [{"id": "b"}, {"id": "c"}]}}},
        ])

        result = get_neo_feed_chunked("2025-01-01", "2025-01-10")

        assert result["element_count"] == 3
        assert result["near_earth_objects"]["2025-01-01"] == [{"id": "a"}]
        assert result["near_earth_objects"]["2025-01-08"] == [{"id": "b"}, {"id": "c"}]

    def test_caches_the_full_range_and_skips_refetching_chunks(self, requests_mock):
        requests_mock.get(FEED_URL, [
            {"json": {"element_count": 0, "near_earth_objects": {}}},
            {"json": {"element_count": 0, "near_earth_objects": {}}},
        ])

        get_neo_feed_chunked("2025-01-01", "2025-01-10")
        get_neo_feed_chunked("2025-01-01", "2025-01-10")

        # 2 chunk requests for the first call; the second call should hit
        # the chunked-level cache and make zero further requests.
        assert requests_mock.call_count == 2
