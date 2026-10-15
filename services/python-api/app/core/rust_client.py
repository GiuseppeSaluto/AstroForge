import requests
from dataclasses import dataclass
from typing import Dict, Any

from app.core.config import RUST_ENGINE_URL, REQUEST_TIMEOUT
from app.utils.logger import logger


@dataclass
class BatchResult:
    results: list[Dict[str, Any]]
    errors: list[Dict[str, Any]]


def process_asteroid_batch_with_rust(asteroid_dtos: list[Dict[str, Any]]) -> BatchResult:
    if not RUST_ENGINE_URL:
        raise RuntimeError("RUST_ENGINE_URL is not configured.")

    url = f"{RUST_ENGINE_URL}/api/process/batch"
    logger.info(f"Sending batch of {len(asteroid_dtos)} asteroids to Rust Engine")

    try:
        response = requests.post(url, json=asteroid_dtos, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Rust Engine batch request failed: {e}")
        raise

    try:
        payload = response.json()
    except ValueError as e:
        raise RuntimeError("Rust Engine returned invalid JSON for batch") from e

    batch = BatchResult(results=payload["results"], errors=payload["errors"])
    logger.info(
        f"Received {len(batch.results)} results and {len(batch.errors)} errors "
        "from Rust Engine batch"
    )
    return batch


def check_rust_health() -> str:
    """Check if Rust engine is reachable and healthy."""
    if not RUST_ENGINE_URL:
        return "unconfigured"
    
    try:
        # Try to reach the Rust engine health endpoint
        response = requests.get(
            f"{RUST_ENGINE_URL}/api/health",
            timeout=5
        )
        if response.status_code == 200:
            return "ok"
        else:
            logger.warning(f"Rust Engine returned status {response.status_code}")
            return "unhealthy"
    except requests.RequestException as e:
        logger.warning(f"Rust Engine health check failed: {e}")
        return "unreachable"