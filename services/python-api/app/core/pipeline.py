from app.core.dto_mapper import map_mongo_document_to_asteroid
from app.core.mongodb import get_mongo
from app.core.rust_client import process_asteroid_batch_with_rust
from app.utils.logger import logger


def analyze_unprocessed_asteroids(limit: int = 100) -> dict:
    mongo = get_mongo()

    logger.info(f"Starting analysis pipeline for up to {limit} asteroids")

    stats = {
        "total_fetched": 0,
        "processed": 0,
        "failed": 0,
        "skipped": 0,
    }

    raw_asteroids = mongo.get_unprocessed_asteroids(limit=limit)
    stats["total_fetched"] = len(raw_asteroids)
    logger.info(f"Fetched {len(raw_asteroids)} unprocessed asteroids")

    # Map raw documents to domain objects, skipping any that fail validation
    asteroids = []
    for raw_doc in raw_asteroids:
        asteroid_id = raw_doc.get("asteroid", {}).get("id", "unknown")
        mapped = map_mongo_document_to_asteroid(raw_doc)
        if mapped is None:
            logger.warning(f"Skipping asteroid {asteroid_id}: mapping failed")
            stats["skipped"] += 1
        else:
            asteroids.append(mapped)

    if not asteroids:
        logger.info("No asteroids to process after mapping")
        return stats

    # Send the entire batch to the Rust Engine in a single request.
    # A connection/HTTP error is not caught here: it reaches the global
    # RequestException handler as a 503 "Rust Engine unreachable", instead
    # of a 200 "success" with every asteroid silently counted as failed.
    # Nothing has been saved yet, so the asteroids stay unprocessed and
    # the next run picks them up.
    dto_list = [a.to_dto_dict() for a in asteroids]
    batch = process_asteroid_batch_with_rust(dto_list)

    for risk_result in batch.results:
        asteroid_id = risk_result.get("asteroid_id", "unknown")
        try:
            mongo.save_analysis_result(asteroid_id, risk_result)
            stats["processed"] += 1
            logger.info(
                f"Saved analysis for asteroid {asteroid_id} "
                f"(risk: {risk_result.get('risk_level', 'unknown')})"
            )
        except Exception as e:
            logger.error(f"Failed to save result for asteroid {asteroid_id}: {e}")
            stats["failed"] += 1

    for err in batch.errors:
        logger.warning(f"Asteroid {err['id']} rejected by Rust Engine: {err['details']}")
        stats["skipped"] += 1

    logger.info(
        f"Pipeline completed: {stats['processed']} processed, "
        f"{stats['failed']} failed, {stats['skipped']} skipped"
    )

    return stats
