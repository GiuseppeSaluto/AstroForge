from datetime import datetime, timezone

from flask import current_app
from pymongo import MongoClient

from app.utils.logger import logger

# collection -> [(field, unique)]. create_index also creates the collection
# if it doesn't exist yet, so no separate create_collection step is needed.
_INDEXES = {
    "nasa_feeds": [("retrieved_at", False), ("feed_start_date", False), ("feed_end_date", False)],
    "asteroid_analyses": [("neo_reference_id", True), ("analysis_timestamp", False)],
    "asteroids_raw": [("date", False), ("asteroid.id", True), ("stored_at", False)],
}


class MongoDBClient:
    def __init__(self, uri: str, db_name: str):
        # connect=False: no network I/O until the first query, so building
        # the client can't fail and `self.db` is never None — which is what
        # lets every method below skip an "is the DB initialized?" check.
        # tz_aware=True: datetimes come back as UTC-aware. Without it pymongo
        # returns naive datetimes, `.isoformat()` drops the "+00:00", and the
        # dashboard's `.astimezone()` then misreads them as local time.
        self.uri = uri
        self.client = MongoClient(
            uri,
            connect=False,
            tz_aware=True,
            serverSelectionTimeoutMS=3000,
            maxPoolSize=50,
            minPoolSize=5,
            maxIdleTimeMS=60000,
        )
        self.db = self.client[db_name]

    # Flask
    def init_app(self, app):
        # First real round-trip: raises PyMongoError here, at startup, if
        # Mongo is unreachable.
        for collection, indexes in _INDEXES.items():
            for field, unique in indexes:
                self.db[collection].create_index(field, unique=unique)
        logger.info(f"Connected to MongoDB at {self.uri}, using DB '{self.db.name}'")
        app.extensions["mongo"] = self

    def ping(self) -> None:
        """Cheap liveness check; raises PyMongoError if the server is unreachable."""
        self.client.admin.command("ping")

    # CRUD — PyMongoError is left to propagate: callers and the global
    # error handler already log it, so no per-method try/except here.
    def save_nasa_feed(self, feed: dict):
        result = self.db["nasa_feeds"].insert_one(feed)
        logger.info(f"Inserted NASA feed with id {result.inserted_id}")
        return result.inserted_id

    def save_raw_asteroid(self, date: str, asteroid: dict) -> bool:
        """Upsert a raw asteroid. Returns True if newly inserted, False if it already existed."""
        asteroid_id = asteroid.get("id") or asteroid.get("neo_reference_id", "")
        result = self.db["asteroids_raw"].update_one(
            {"asteroid.id": asteroid_id},
            {"$setOnInsert": {
                "date": date,
                "asteroid": asteroid,
                "stored_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
        is_new = result.upserted_id is not None
        if is_new:
            logger.info(f"Inserted raw asteroid {asteroid_id} for {date}")
        return is_new

    def get_raw_asteroid_by_id(self, asteroid_id: str) -> dict | None:
        return self.db["asteroids_raw"].find_one({"asteroid.id": asteroid_id})

    def get_unprocessed_asteroids(self, limit: int = 100) -> list[dict]:
        pipeline = [
            {"$lookup": {
                "from": "asteroid_analyses",
                "localField": "asteroid.id",
                "foreignField": "neo_reference_id",
                "as": "existing_analysis",
            }},
            {"$match": {"existing_analysis": {"$size": 0}}},
            {"$project": {"existing_analysis": 0}},
            {"$limit": limit},
        ]
        result = list(self.db["asteroids_raw"].aggregate(pipeline))
        logger.info(f"Found {len(result)} unprocessed asteroids")
        return result

    def save_analysis_result(self, asteroid_id: str, risk_result: dict) -> None:
        result = self.db["asteroid_analyses"].update_one(
            {"neo_reference_id": asteroid_id},
            {"$set": {
                "neo_reference_id": asteroid_id,
                "analysis_timestamp": datetime.now(timezone.utc),
                "risk_data": risk_result,
            }},
            upsert=True,
        )
        action = "Inserted" if result.upserted_id else "Updated"
        logger.info(f"{action} analysis for asteroid {asteroid_id}")

    def get_pipeline_stats(self) -> dict:
        """Aggregate counts backing the /pipeline/stats endpoint."""
        raw_collection = self.db["asteroids_raw"]
        analysis_collection = self.db["asteroid_analyses"]

        pipeline = [
            {"$lookup": {
                "from": "asteroid_analyses",
                "localField": "asteroid.id",
                "foreignField": "neo_reference_id",
                "as": "analysis",
            }},
            {"$match": {"analysis": {"$size": 0}}},
            {"$count": "unprocessed"},
        ]
        agg_result = list(raw_collection.aggregate(pipeline))
        unprocessed = agg_result[0]["unprocessed"] if agg_result else 0

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        analyzed_today = analysis_collection.count_documents({
            "analysis_timestamp": {"$gte": today_start}
        })

        high_risks = analysis_collection.count_documents({
            "risk_data.risk_level": {"$in": ["High", "Critical"]}
        })

        total_analyzed = analysis_collection.count_documents({})

        last_run = analysis_collection.find_one(sort=[("analysis_timestamp", -1)])

        return {
            "unprocessed": unprocessed,
            "analyzed_today": analyzed_today,
            "total_analyzed": total_analyzed,
            "high_risks": high_risks,
            "last_pipeline_run": last_run["analysis_timestamp"] if last_run else None,
        }

    def get_close_approaches(self, limit: int = 10) -> list[dict]:
        """NEOs sorted by miss distance, enriched with risk data from the latest analysis."""
        pipeline = [
            {"$unwind": "$asteroid.close_approach_data"},
            {"$lookup": {
                "from": "asteroid_analyses",
                "localField": "asteroid.id",
                "foreignField": "neo_reference_id",
                "as": "analysis",
            }},
            {"$project": {
                "name": "$asteroid.name",
                "is_hazardous": "$asteroid.is_potentially_hazardous_asteroid",
                "close_approach_date": "$asteroid.close_approach_data.close_approach_date",
                "miss_km": {"$toDouble": "$asteroid.close_approach_data.miss_distance.kilometers"},
                "velocity_kps": {"$toDouble": "$asteroid.close_approach_data.relative_velocity.kilometers_per_second"},
                "risk_level": {"$arrayElemAt": ["$analysis.risk_data.risk_level", 0]},
                "risk_score": {"$arrayElemAt": ["$analysis.risk_data.risk_score_0_to_100", 0]},
                "diameter_km": {"$arrayElemAt": ["$analysis.risk_data.diameter_km", 0]},
            }},
            {"$sort": {"miss_km": 1}},
            {"$limit": limit},
        ]
        return list(self.db["asteroids_raw"].aggregate(pipeline))

    def get_analyzed_asteroids(self, limit: int, sort_field: str, sort_dir: int) -> list[dict]:
        """Analyzed asteroids sorted by the given risk_data field."""
        cursor = (
            self.db["asteroid_analyses"]
            .find({}, {"_id": 0})
            .sort(sort_field, sort_dir)
            .limit(limit)
        )
        return list(cursor)


def get_mongo() -> MongoDBClient:
    """The MongoDBClient that init_app registered on the current Flask app."""
    mongo = current_app.extensions.get("mongo")
    if mongo is None:
        raise RuntimeError("MongoDB extension not initialized")
    return mongo
