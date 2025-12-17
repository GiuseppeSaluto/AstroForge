import requests
from typing import Optional, Dict, Any
from datetime import date, timedelta

from app.core.config import NASA_API_KEY, NASA_BASE_URL, NASA_APOD_ENDPOINT, NASA_NEO_FEED_ENDPOINT, REQUEST_TIMEOUT

from app.utils.logger import logger


def _build_nasa_url(endpoint: str, params: Optional[Dict[str, str]] = None) -> tuple[str, Dict[str, str]]:
    final_params = {"api_key": NASA_API_KEY}
    if params:
        final_params.update({k: str(v) for k, v in params.items()})

    url = f"{NASA_BASE_URL}{endpoint}"
    return url, final_params


def get_apod(date_str: Optional[str] = None) -> Dict[str, Any]:
    params = {}
    if date_str:
        params["date"] = date_str

    url, query = _build_nasa_url(NASA_APOD_ENDPOINT, params)

    logger.info(f"Calling NASA APOD: {url} params={query}")

    response = requests.get(url, params=query, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    return response.json()


def get_neo_feed(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    if start_date is None:
        start_date = date.today().strftime("%Y-%m-%d")

    if end_date is None:
        end_date_date = date.fromisoformat(start_date) + timedelta(days=7)
        end_date = end_date_date.strftime("%Y-%m-%d")

    params = {
        "start_date": start_date,
        "end_date": end_date,
    }

    url, query = _build_nasa_url(NASA_NEO_FEED_ENDPOINT, params)

    logger.info(f"Calling NASA NEO Feed: {url} params={query}")

    response = requests.get(url, params=query, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    return response.json()
