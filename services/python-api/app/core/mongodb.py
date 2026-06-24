from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from flask import current_app
from datetime import datetime, timezone

from app.utils.logger import logger


class MongoDBClient:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name

        self.client: MongoClient | None = None
        self.db: Database | None = None
        
    # Flask
    def init_app(self, app):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=3000, maxPoolSize=50, minPoolSize=5,maxIdleTimeMS=60000)
            self.db = self.client[self.db_name]

            logger.info(f"Connected to MongoDB at {self.uri}, using DB '{self.db_name}'")

            self._ensure_collections()

            if not hasattr(app, 'extensions'):
                app.extensions = {}
            app.extensions["mongo"] = self

        except PyMongoError as e:
            logger.critical(f"Failed to initialize MongoDB: {e}")
            raise
        
    # DB
    def _ensure_collections(self):
        if self.db is None:
            raise RuntimeError("Database not initialized. Call init_app() first.")
        
        required_collections = {
            "nasa_feeds": self._init_nasa_feeds,
            "asteroid_analyses": self._init_asteroid_analyses,
            "asteroids_raw": self._init_asteroids_raw,
        }

        existing = self.db.list_collection_names()

        for name, initializer in required_collections.items():
            if name not in existing:
                self.db.create_collection(name)
                logger.info(f"Created MongoDB collection '{name}'")
            initializer()

    def _init_nasa_feeds(self):
        if self.db is None:
            raise RuntimeError("Database not initialized")
            
        collection = self.db["nasa_feeds"]
        collection.create_index("retrieved_at")
        collection.create_index("feed_start_date")
        collection.create_index("feed_end_date")
        logger.debug("Initialized indexes for 'nasa_feeds'")

    def _init_asteroid_analyses(self):
        if self.db is None:
            raise RuntimeError("Database not initialized")

        collection = self.db["asteroid_analyses"]
        collection.create_index("neo_reference_id", unique=True)
        collection.create_index("analysis_timestamp")
        logger.debug("Initialized indexes for 'asteroid_analyses'")

    def _init_asteroids_raw(self):
        if self.db is None:
            raise RuntimeError("Database not initialized")

        collection = self.db["asteroids_raw"]
        collection.create_index("date")
        collection.create_index("asteroid.id", unique=True)
        collection.create_index("stored_at")
        logger.debug("Initialized indexes for 'asteroids_raw'")

    # CRUD
    def save_nasa_feed(self, feed: dict):
        if self.db is None:
            raise RuntimeError("Database not initialized. Call init_app() first.")
            
        try:
            collection = self.db["nasa_feeds"]
            result = collection.insert_one(feed)
            logger.info(f"Inserted NASA feed with id {result.inserted_id}")
            return result.inserted_id
        except PyMongoError as e:
            logger.error(f"Failed to save NASA feed: {e}")
            raise

    def save_raw_asteroid(self, date: str, asteroid: dict) -> bool:
        """Upsert a raw asteroid. Returns True if newly inserted, False if it already existed."""
        if self.db is None:
            raise RuntimeError("Database not initialized. Call init_app() first.")

        asteroid_id = asteroid.get("id") or asteroid.get("neo_reference_id", "")

        try:
            collection = self.db["asteroids_raw"]
            result = collection.update_one(
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
        except PyMongoError as e:
            logger.error(f"Failed to save raw asteroid {asteroid_id}: {e}")
            raise

    def count_raw_asteroids(self) -> int:
        """Return the total number of raw asteroids stored in the DB."""
        if self.db is None:
            raise RuntimeError("Database not initialized")
        try:
            return self.db["asteroids_raw"].count_documents({})
        except PyMongoError as e:
            logger.error(f"Failed to count raw asteroids: {e}")
            raise

    def get_raw_asteroids_by_date(self, date: str) -> list[dict]:
        if self.db is None:
            raise RuntimeError("Database not initialized")

        try:
            collection = self.db["asteroids_raw"]
            cursor = collection.find({"date": date})
            return list(cursor)
        except PyMongoError as e:
            logger.error(f"Failed to fetch raw asteroids for date {date}: {e}")
            raise

    def get_raw_asteroid_by_id(self, asteroid_id: str) -> dict | None:
        if self.db is None:
            raise RuntimeError("Database not initialized")

        try:
            collection = self.db["asteroids_raw"]
            return collection.find_one({"asteroid.id": asteroid_id})
        except PyMongoError as e:
            logger.error(f"Failed to fetch asteroid {asteroid_id}: {e}")
            raise

    def get_unprocessed_asteroids(self, limit: int = 100) -> list[dict]:
        if self.db is None:
            raise RuntimeError("Database not initialized")

        try:
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

        except PyMongoError as e:
            logger.error(f"Failed to fetch unprocessed asteroids: {e}")
            raise

    def save_analysis_result(self, asteroid_id: str, risk_result: dict) -> None:
        if self.db is None:
            raise RuntimeError("Database not initialized")

        try:
            collection = self.db["asteroid_analyses"]
            result = collection.update_one(
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
        except PyMongoError as e:
            logger.error(f"Failed to save analysis result for {asteroid_id}: {e}")
            raise

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")