import os
import requests
from typing import Dict, List, Any, Optional

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
RUST_ENGINE_URL = os.getenv("RUST_ENGINE_URL", "http://localhost:8080")


def get_status() -> Dict[str, str]:
    status = {"backend": "unknown", "rust_engine": "unknown"}

    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        status["backend"] = "connected" if response.status_code == 200 else "error"
    except requests.RequestException:
        status["backend"] = "unreachable"

    try:
        response = requests.get(f"{RUST_ENGINE_URL}/", timeout=5)
        status["rust_engine"] = "reachable" if response.status_code == 200 else "error"
    except requests.RequestException:
        status["rust_engine"] = "unreachable"

    return status


def run_pipeline(limit: int = 100) -> Dict[str, Any]:
    try:
        response = requests.post(f"{API_BASE_URL}/pipeline/neo/analyze?limit={limit}", timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Pipeline failed with status {response.status_code}"}
    except requests.RequestException as e:
        return {"error": f"Unable to run pipeline: {str(e)}"}


def get_asteroids(start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        response = requests.get(f"{API_BASE_URL}/nasa/neo/feed", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("near_earth_objects", [])
        else:
            return []
    except requests.RequestException:
        return []


def get_logs() -> List[str]:
    try:
        response = requests.get(f"{API_BASE_URL}/logs", timeout=10)
        if response.status_code == 200:
            return response.json().get("logs", [])
        else:
            return []
    except requests.RequestException:
        return []