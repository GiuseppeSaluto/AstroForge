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
        raise ValueError("RUST_ENGINE_URL is not configured.")

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


def process_asteroid_with_rust(asteroid_dto: Dict[str, Any]) -> Dict[str, Any]:
    if not RUST_ENGINE_URL:
        raise ValueError("RUST_ENGINE_URL is not configured.")

    url = f"{RUST_ENGINE_URL}/api/process/asteroid"
    asteroid_id = asteroid_dto.get("id", "unknown")

    logger.info(f"Sending asteroid {asteroid_id} to Rust Engine")

    try:
        response = requests.post(url, json=asteroid_dto, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Rust Engine request failed for asteroid {asteroid_id}: {e}")
        raise

    try:
        result = response.json()
    except ValueError as e:
        logger.error(
            f"Invalid JSON response from Rust Engine for asteroid {asteroid_id}"
        )
        raise RuntimeError("Rust Engine returned invalid JSON") from e

    if "asteroid_id" not in result:
        logger.warning(
            f"Rust Engine response missing asteroid_id field: {result}"
        )

    logger.info(
        f"Received risk analysis for asteroid {result.get('asteroid_id', 'unknown')}"
    )

    return result


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