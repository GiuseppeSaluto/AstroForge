import os
import requests
import logging
from typing import Dict, List, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5001")

DEFAULT_TIMEOUT = 15
REQUEST_TIMEOUT = 20

def _create_session_with_retries() -> requests.Session:
    """Create a requests session with retry strategy."""
    session = requests.Session()

    # POST is deliberately not retried: "Run pipeline" is not a read, and
    # retrying it on a 500/503 just re-runs the work and keeps the button
    # hanging for up to 4x REQUEST_TIMEOUT before showing the failure.
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

_session = _create_session_with_retries()


def _request(method: str, path: str, timeout: int = DEFAULT_TIMEOUT, **kwargs) -> tuple[Any, Optional[str]]:
    """Call the Python API.

    Returns (json, None) on success and (None, error message) on any
    failure — network error, HTTP error status, or a non-JSON body
    (requests' JSONDecodeError is a RequestException too). Screens never
    see an exception; each public function below picks its own fallback.
    """
    try:
        response = _session.request(method, f"{API_BASE_URL}{path}", timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as e:
        logger.error(f"{method} {path} failed: {e}")
        # Prefer the API's own JSON message (e.g. "Rust Engine unreachable")
        # over requests' generic "503 Server Error: ... for url ..." text.
        # e.response is None for network errors, hence AttributeError.
        try:
            return None, e.response.json()["error"]
        except (AttributeError, ValueError, KeyError, TypeError):
            return None, str(e)

# =====================================================================
# HEALTH & STATUS
# =====================================================================

def get_system_status() -> Dict[str, Any]:
    """Get overall system health status (Python API reports Mongo + Rust)."""
    backend, error = _request("GET", "/pipeline/status")
    if error:
        backend = {"status": "unreachable", "error": error}

    rust_ok = backend.get("components", {}).get("rust_engine") == "ok"
    return {
        "backend": backend,
        "rust_engine": {"status": "ok" if rust_ok else "unreachable"},
    }

# =====================================================================
# PIPELINE
# =====================================================================

def get_pipeline_stats() -> Dict[str, Any]:
    """Get pipeline statistics (unprocessed, analyzed today, high risks)."""
    stats, error = _request("GET", "/pipeline/stats")
    if error:
        return {"status": "error", "error": error}
    return stats


def run_pipeline(limit: int = 100) -> Dict[str, Any]:
    """Trigger pipeline analysis for unprocessed asteroids."""
    result, error = _request("POST", "/pipeline/neo/analyze", timeout=REQUEST_TIMEOUT, params={"limit": limit})
    if error:
        return {"status": "error", "error": error}
    return result

# =====================================================================
# DATA ACCESS
# =====================================================================

def get_analyzed_asteroids(limit: int = 200, sort: str = "risk", order: str = "desc") -> List[Dict[str, Any]]:
    """Get list of analyzed asteroids. `sort` is one of: risk, energy, date."""
    params = {"limit": limit, "sort": sort, "order": order}
    asteroids, _ = _request("GET", "/pipeline/analysis/asteroids", timeout=REQUEST_TIMEOUT, params=params)
    return asteroids or []


def get_close_approaches(limit: int = 10) -> List[Dict[str, Any]]:
    """Get NEOs sorted by miss distance, enriched with Rust Engine risk data."""
    approaches, _ = _request("GET", "/pipeline/close-approaches", params={"limit": limit})
    return approaches or []


def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent logs from Python API."""
    logs, _ = _request("GET", "/logs", params={"limit": limit})
    return logs or []


def get_asteroid_detail(asteroid_id: str) -> dict:
    """Fetch full asteroid detail (close approaches + orbital data) from NASA via Python API."""
    detail, _ = _request("GET", f"/nasa/asteroids/{asteroid_id}", timeout=REQUEST_TIMEOUT)
    return detail or {}


def get_nasa_asteroids(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_hazardous: Optional[bool] = None,
    sort_by: str = "distance",
    order: str = "asc",
) -> List[Dict[str, Any]]:
    """Get normalized asteroid list from the filterable /nasa/asteroids endpoint."""
    params: Dict[str, Any] = {"sort_by": sort_by, "order": order}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if is_hazardous is not None:
        params["is_hazardous"] = str(is_hazardous).lower()

    data, _ = _request("GET", "/nasa/asteroids", timeout=REQUEST_TIMEOUT, params=params)
    return (data or {}).get("asteroids", [])
