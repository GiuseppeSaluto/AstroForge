import os
import requests
import logging
from typing import Dict, List, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5001")
RUST_ENGINE_URL = os.getenv("RUST_ENGINE_URL", "http://localhost:8080")

DEFAULT_TIMEOUT = 15
REQUEST_TIMEOUT = 20

def _create_session_with_retries() -> requests.Session:
    """Create a requests session with retry strategy."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

_session = _create_session_with_retries()

# =====================================================================
# HEALTH & STATUS
# =====================================================================

def get_backend_health() -> Dict[str, Any]:
    """Check Python API health."""
    try:
        response = _session.get(
            f"{API_BASE_URL}/pipeline/status",
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Backend health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}

def get_rust_health() -> Dict[str, Any]:
    """Check Rust engine health via Python API status."""
    try:
        response = _session.get(
            f"{API_BASE_URL}/pipeline/status",
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        rust_status = data.get("components", {}).get("rust_engine", "unknown")
        return {"status": "ok" if rust_status == "ok" else "unreachable"}
    except requests.RequestException as e:
        logger.warning(f"Rust health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}

def get_system_status() -> Dict[str, Any]:
    """Get overall system health status."""
    backend = get_backend_health()
    rust = get_rust_health()
    
    return {
        "backend": backend,
        "rust_engine": rust,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

# =====================================================================
# PIPELINE STATISTICS
# =====================================================================

def get_pipeline_stats() -> Dict[str, Any]:
    """Get pipeline statistics (unprocessed, analyzed today, high risks)."""
    try:
        response = _session.get(
            f"{API_BASE_URL}/pipeline/stats",
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get pipeline stats: {e}")
        return {
            "status": "error",
            "unprocessed": 0,
            "analyzed_today": 0,
            "high_risks": 0,
            "last_pipeline_run": None,
            "error": str(e)
        }

# =====================================================================
# ACTIONS
# =====================================================================

def run_pipeline(limit: int = 100) -> Dict[str, Any]:
    """Trigger pipeline analysis for unprocessed asteroids."""
    try:
        response = _session.post(
            f"{API_BASE_URL}/pipeline/neo/analyze",
            params={"limit": limit},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Pipeline execution failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "statistics": {"processed": 0, "failed": 0, "skipped": 0}
        }

# =====================================================================
# DATA ACCESS
# =====================================================================

def get_analyzed_asteroids(
    limit: int = 200, 
    sort: str = "risk_score", 
    order: str = "desc"
) -> List[Dict[str, Any]]:
    """Get list of analyzed asteroids."""
    try:
        response = _session.get(
            f"{API_BASE_URL}/pipeline/analysis/asteroids",
            params={
                "limit": limit,
                "sort": sort,
                "order": order,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        
        # Handle both direct list and wrapped response
        if isinstance(data, list):
            return data
        return data.get("asteroids", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get analyzed asteroids: {e}")
        return []

def get_close_approaches(limit: int = 10) -> List[Dict[str, Any]]:
    """Get NEOs sorted by miss distance, enriched with Rust Engine risk data."""
    try:
        response = _session.get(
            f"{API_BASE_URL}/pipeline/close-approaches",
            params={"limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get close approaches: {e}")
        return []


def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent logs from Python API."""
    try:
        response = _session.get(
            f"{API_BASE_URL}/logs",
            params={"limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list):
            return data
        return data.get("logs", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get logs: {e}")
        return []

def get_asteroid_detail(asteroid_id: str) -> dict:
    """Fetch full asteroid detail (close approaches + orbital data) from NASA via Python API."""
    try:
        response = _session.get(
            f"{API_BASE_URL}/nasa/asteroids/{asteroid_id}",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get asteroid detail for {asteroid_id}: {e}")
        return {}


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

    try:
        response = _session.get(
            f"{API_BASE_URL}/nasa/asteroids",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("asteroids", [])
    except requests.RequestException as e:
        logger.error(f"Failed to get NASA asteroids: {e}")
        return []