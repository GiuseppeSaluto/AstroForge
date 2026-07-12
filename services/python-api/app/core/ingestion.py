from datetime import datetime, timezone
from typing import Optional

from flask import current_app

from app.core.mongodb import MongoDBClient
from app.core.nasa_client import get_neo_feed
from app.utils.logger import logger


class IngestionPipeline:
    """Fetches a NEO feed from NASA, persists new asteroids, and logs the fetch."""

    @staticmethod
    def ingest_neo_feed(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        mongo: MongoDBClient | None = current_app.extensions.get("mongo")
        if not mongo:
            raise RuntimeError("MongoDB extension not initialized")

        feed = get_neo_feed(start_date=start_date, end_date=end_date)
        if not feed or "near_earth_objects" not in feed:
            raise ValueError("Invalid feed from NASA")

        near_earth_objects = feed["near_earth_objects"]

        saved = 0
        skipped = 0
        for date_str, asteroids in near_earth_objects.items():
            for asteroid in asteroids:
                is_new = mongo.save_raw_asteroid(date_str, asteroid)
                if is_new:
                    saved += 1
                else:
                    skipped += 1

        dates = sorted(near_earth_objects.keys())
        resolved_start = dates[0] if dates else start_date
        resolved_end = dates[-1] if dates else end_date

        mongo.save_nasa_feed({
            "retrieved_at": datetime.now(timezone.utc),
            "feed_start_date": resolved_start,
            "feed_end_date": resolved_end,
            "total_in_feed": saved + skipped,
            "saved": saved,
            "skipped": skipped,
        })

        logger.info(f"NEO ingestion complete: {saved} saved, {skipped} skipped")

        return {"saved": saved, "skipped": skipped, "total_in_feed": saved + skipped}
