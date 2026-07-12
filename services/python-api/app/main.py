import threading
from datetime import date, timedelta
from flask import Flask
from app.core.mongodb import MongoDBClient
from app.core.config import DEBUG, MONGO_URI, MONGO_DB_NAME
from app.core.ingestion import IngestionPipeline

# API routes
from app.routes.nasa import nasa_bp
from app.routes.orchestration import orchestration_bp
from app.routes.logs import logs_bp

from app.utils.error_handlers import register_error_handlers
from app.utils.logger import logger


def _seed_asteroids_on_startup(app: Flask) -> None:
    """Fetch the last 7 days of NASA NEO data and save only new asteroids."""
    with app.app_context():
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            logger.info(f"Startup seed: fetching NEO data {start_str} → {end_str}...")
            result = IngestionPipeline.ingest_neo_feed(start_date=start_str, end_date=end_str)

            logger.info(
                f"Startup seed complete: {result['saved']} new asteroids saved, "
                f"{result['skipped']} already present"
            )

        except Exception as e:
            logger.error(f"Startup seed failed: {e}")


def create_app():
    app = Flask(__name__)

    mongo = MongoDBClient(MONGO_URI, MONGO_DB_NAME)
    mongo.init_app(app)

    app.register_blueprint(nasa_bp)
    app.register_blueprint(orchestration_bp)
    app.register_blueprint(logs_bp)

    register_error_handlers(app)

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