import threading
from datetime import date, timedelta
from flask import Flask
from app.core.mongodb import MongoDBClient
from app.core.config import DEBUG, MONGO_URI, MONGO_DB_NAME
from app.core.nasa_client import get_neo_feed

# API routes
from app.routes.nasa import nasa_bp
from app.routes.analysis import analysis_bp
from app.routes.orchestration import orchestration_bp
from app.routes.logs import logs_bp

from app.utils.logger import logger


def _seed_asteroids_on_startup(app: Flask) -> None:
    """Fetch the last 7 days of NASA NEO data and save only new asteroids."""
    with app.app_context():
        try:
            mongo = app.extensions.get("mongo")
            if not mongo:
                logger.warning("Startup seed skipped: MongoDB not ready")
                return

            # Fetch last 7 days from today
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            logger.info(f"Startup seed: fetching NEO data {start_str} → {end_str}...")
            feed = get_neo_feed(start_date=start_str, end_date=end_str)

            if not feed or "near_earth_objects" not in feed:
                logger.error("Startup seed failed: invalid response from NASA API")
                return

            # Build set of asteroid IDs already in DB to avoid duplicates
            existing_ids: set[str] = set()
            if mongo.db is not None:
                for doc in mongo.db["asteroids_raw"].find(
                    {}, {"asteroid.id": 1, "asteroid.neo_reference_id": 1}
                ):
                    ast = doc.get("asteroid", {})
                    existing_ids.add(ast.get("neo_reference_id", ast.get("id", "")))

            saved = 0
            skipped = 0
            for date_str, asteroids in feed["near_earth_objects"].items():
                for asteroid in asteroids:
                    asteroid_id = asteroid.get("neo_reference_id", asteroid.get("id", ""))
                    if asteroid_id in existing_ids:
                        skipped += 1
                        continue
                    mongo.save_raw_asteroid(date_str, asteroid)
                    existing_ids.add(asteroid_id)
                    saved += 1

            logger.info(
                f"Startup seed complete: {saved} new asteroids saved, {skipped} already present"
            )

        except Exception as e:
            logger.error(f"Startup seed failed: {e}")


def create_app():
    app = Flask(__name__)

    mongo = MongoDBClient(MONGO_URI, MONGO_DB_NAME)
    mongo.init_app(app)

    app.register_blueprint(nasa_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(orchestration_bp)
    app.register_blueprint(logs_bp)

    seed_thread = threading.Thread(
        target=_seed_asteroids_on_startup,
        args=(app,),
        daemon=True,
        name="startup-seed",
    )
    seed_thread.start()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=DEBUG)