import os
import requests
from typing import Dict, List, Any, Optional

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")
RUST_ENGINE_URL = os.getenv("RUST_ENGINE_URL", "http://localhost:8080")

DEFAULT_TIMEOUT = 5

# ---------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------
def get_backend_health() -> Dict[str, Any]:
    try:
        response = requests.get(
            f"{API_BASE_URL}/pipeline/status",
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {"status": "unreachable"}

def get_rust_health() -> Dict[str, Any]:
    try:
        response = requests.get(f"{RUST_ENGINE_URL}/health", timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {"status": "unreachable"}


def get_system_status() -> Dict[str, Any]:
    return {
        "backend": get_backend_health(),
        "rust_engine": get_rust_health(),
    }


# ---------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------
def run_pipeline(limit: int = 100) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/pipeline/neo/analyze",
            params={"limit": limit},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------
# Data access (future use)
# ---------------------------------------------------------------------
def get_asteroids(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    try:
        response = requests.get(
            f"{API_BASE_URL}/nasa/neo/feed",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("near_earth_objects", [])
    except requests.RequestException:
        return []

def get_analyzed_asteroids(limit: int = 200, sort: str = "risk", order: str = "desc"):
    try:
        response = requests.get(
            f"{API_BASE_URL}/pipeline/analysis/asteroids",
            params={
                "limit": limit,
                "sort": sort,
                "order": order,
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []