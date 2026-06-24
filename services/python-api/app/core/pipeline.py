from flask import current_app
from requests.exceptions import RequestException

from app.core.dto_mapper import map_mongo_document_to_asteroid
from app.core.mongodb import MongoDBClient
from app.core.rust_client import process_asteroid_batch_with_rust, process_asteroid_with_rust
from app.utils.logger import logger


class AnalysisPipeline:
      
    @staticmethod
    def analyze_unprocessed_asteroids(limit: int = 100) -> dict:
        mongo: MongoDBClient | None = current_app.extensions.get("mongo")
        if not mongo:
            raise RuntimeError("MongoDB extension not initialized")
        
        logger.info(f"Starting analysis pipeline for up to {limit} asteroids")
        
        stats = {
            "total_fetched": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
        }
        
        try:
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

            # Send the entire batch to the Rust Engine in a single request
            dto_list = [a.to_dto_dict() for a in asteroids]
            id_to_asteroid = {a.id: a for a in asteroids}

            try:
                results = process_asteroid_batch_with_rust(dto_list)
            except RequestException as e:
                logger.error(f"Rust engine batch request failed: {e}")
                stats["failed"] += len(asteroids)
                return stats

            # Index results by asteroid_id and persist each one
            returned_ids = set()
            for risk_result in results:
                asteroid_id = risk_result.get("asteroid_id", "unknown")
                returned_ids.add(asteroid_id)
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

            # Any asteroid that was sent but not returned was skipped by Rust (validation)
            for a in asteroids:
                if a.id not in returned_ids:
                    logger.warning(f"Asteroid {a.id} was not returned by Rust Engine (validation skipped)")
                    stats["skipped"] += 1
            
            logger.info(
                f"Pipeline completed: {stats['processed']} processed, "
                f"{stats['failed']} failed, {stats['skipped']} skipped"
            )
            
            return stats
            
        except Exception as e:
            logger.critical(f"Pipeline failed: {e}")
            raise


    @staticmethod
    def analyze_single_asteroid(asteroid_id: str) -> dict:
        
        mongo: MongoDBClient | None = current_app.extensions.get("mongo")
        if not mongo:
            raise RuntimeError("MongoDB extension not initialized")
        
        logger.info(f"Analyzing single asteroid: {asteroid_id}")
        
        raw_doc = mongo.get_raw_asteroid_by_id(asteroid_id)
        
        if not raw_doc:
            raise ValueError(f"Asteroid {asteroid_id} not found in database")
        
        asteroid = map_mongo_document_to_asteroid(raw_doc)
        if asteroid is None:
            raise ValueError(f"Asteroid {asteroid_id} mapping failed")
        
        asteroid_dto = asteroid.to_dto_dict()
        
        risk_result = process_asteroid_with_rust(asteroid_dto)
        
        mongo.save_analysis_result(asteroid.id, risk_result)
        
        logger.info(f"Single asteroid analysis complete: {asteroid_id}")
        
        return risk_result
