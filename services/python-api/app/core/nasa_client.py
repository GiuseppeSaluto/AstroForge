import time
import requests
from typing import Optional, Dict, Any
from datetime import date, timedelta

from app.core.config import (
    NASA_API_KEY,
    NASA_BASE_URL,
    NASA_APOD_ENDPOINT,
    NASA_NEO_FEED_ENDPOINT,
    NASA_NEO_LOOKUP_ENDPOINT,
    REQUEST_TIMEOUT,
)
from app.core.cache import cache_get, cache_set
from app.utils.logger import logger

_MAX_FEED_DAYS = 7


def _build_nasa_url(endpoint: str, params: Optional[Dict[str, str]] = None) -> tuple[str, Dict[str, str]]:
    final_params = {"api_key": NASA_API_KEY}
    if params:
        final_params.update({k: str(v) for k, v in params.items()})
    return f"{NASA_BASE_URL}{endpoint}", final_params


def _get_with_retry(url: str, params: Dict, max_retries: int = 3) -> requests.Response:
    """GET with exponential backoff on 429 rate limit."""
    for attempt in range(max_retries):
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        wait = 2 ** attempt
        logger.warning(f"NASA API rate limit hit, retrying in {wait}s ({attempt + 1}/{max_retries})")
        time.sleep(wait)
    raise requests.exceptions.HTTPError("NASA API rate limit exceeded after all retries")


def get_apod(date_str: Optional[str] = None) -> Dict[str, Any]:
    params = {}
    if date_str:
        params["date"] = date_str
    url, query = _build_nasa_url(NASA_APOD_ENDPOINT, params)
    logger.info(f"Calling NASA APOD: {url}")
    response = _get_with_retry(url, query)
    return response.json()


def get_neo_feed(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Fetch NEO feed for a single window of max 7 days."""
    if start_date is None:
        start_date = date.today().strftime("%Y-%m-%d")
    if end_date is None:
        end_date = (date.fromisoformat(start_date) + timedelta(days=_MAX_FEED_DAYS - 1)).strftime("%Y-%m-%d")

    cache_key = f"neo_feed:{start_date}:{end_date}"
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info(f"Cache HIT — NEO feed {start_date}→{end_date}")
        return cached

    url, query = _build_nasa_url(NASA_NEO_FEED_ENDPOINT, {"start_date": start_date, "end_date": end_date})
    logger.info(f"Calling NASA NEO Feed: {start_date}→{end_date}")
    response = _get_with_retry(url, query)
    result = response.json()

    cache_set(cache_key, result)
    return result


def get_neo_feed_chunked(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Fetch NEO feed for any date range by splitting into 7-day chunks.
    Results are aggregated into a single near_earth_objects dict.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    cache_key = f"neo_feed_chunked:{start_date}:{end_date}"
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info(f"Cache HIT — chunked feed {start_date}→{end_date}")
        return cached

    aggregated: Dict[str, list] = {}
    total_count = 0

    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=_MAX_FEED_DAYS - 1), end)
        chunk = get_neo_feed(
            start_date=chunk_start.strftime("%Y-%m-%d"),
            end_date=chunk_end.strftime("%Y-%m-%d"),
        )
        for date_key, asteroids in chunk.get("near_earth_objects", {}).items():
            if date_key not in aggregated:
                aggregated[date_key] = []
            aggregated[date_key].extend(asteroids)
            total_count += len(asteroids)

        chunk_start = chunk_end + timedelta(days=1)

    result = {"element_count": total_count, "near_earth_objects": aggregated}
    cache_set(cache_key, result)
    logger.info(f"Chunked feed complete: {total_count} NEOs across {len(aggregated)} days")
    return result


def get_asteroid_detail(asteroid_id: str) -> Dict[str, Any]:
    """Fetch full asteroid record from NASA NeoWS lookup endpoint."""
    cache_key = f"neo_detail:{asteroid_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info(f"Cache HIT — asteroid detail {asteroid_id}")
        return cached

    url, query = _build_nasa_url(f"{NASA_NEO_LOOKUP_ENDPOINT}{asteroid_id}")
    logger.info(f"Calling NASA NEO Lookup: {asteroid_id}")
    response = _get_with_retry(url, query)
    result = response.json()

    cache_set(cache_key, result)
    return result
