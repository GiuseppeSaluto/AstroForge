from flask import Blueprint, jsonify, request
from flask import current_app
from datetime import datetime, timezone
from app.core.pipeline import AnalysisPipeline
from app.core.rust_client import check_rust_health
from app.utils.logger import logger

orchestration_bp = Blueprint("orchestration", __name__, url_prefix="/pipeline")

@orchestration_bp.route("/neo/analyze", methods=["POST"])
def analyze_neo_pipeline():
    logger.info("Received request: POST /pipeline/neo/analyze")

    limit = request.args.get("limit", default=100, type=int)

    if limit < 1 or limit > 1000:
        return jsonify({"error": "limit must be between 1 and 1000"}), 400

    stats = AnalysisPipeline.analyze_unprocessed_asteroids(limit=limit)

    logger.info(f"Pipeline completed successfully: {stats}")

    return jsonify(
        {
            "status": "success",
            "statistics": stats,
        }
    ), 200


@orchestration_bp.route("/neo/analyze/<asteroid_id>", methods=["POST"])
def analyze_single_neo(asteroid_id: str):
    logger.info(f"Received request: POST /pipeline/neo/analyze/{asteroid_id}")

    try:
        result = AnalysisPipeline.analyze_single_asteroid(asteroid_id)

        return (
            jsonify(
                {
                    "status": "success",
                    "asteroid_id": asteroid_id,
                    "risk_analysis": result,
                }
            ),
            200,
        )

    except ValueError as e:
        # Route-specific meaning ("asteroid not found or invalid"), so
        # this stays local rather than in the global error handlers —
        # ValueError means something else entirely elsewhere (e.g. a
        # misconfigured RUST_ENGINE_URL in rust_client.py).
        logger.warning(f"Asteroid {asteroid_id} not found or invalid: {e}")
        return (
            jsonify(
                {
                    "error": "Asteroid not found or invalid",
                    "details": str(e),
                }
            ),
            404,
        )

@orchestration_bp.route("/status", methods=["GET"])
def pipeline_status():
    logger.info("Received request: GET /pipeline/status")

    try:
        from flask import current_app

        mongo = current_app.extensions.get("mongo")

        if not mongo:
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "reason": "MongoDB not initialized",
                    }
                ),
                503,
            )

        mongo.get_unprocessed_asteroids(limit=1)
        
        # Check Rust Engine health
        rust_status = check_rust_health()

        return (
            jsonify(
                {
                    "status": "healthy",
                    "components": {
                        "mongodb": "connected",
                        "rust_engine": rust_status,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Pipeline status check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@orchestration_bp.route("/stats", methods=["GET"])
def pipeline_stats():
    
    logger.info("Received request: GET /pipeline/stats")

    mongo = current_app.extensions.get("mongo")
    if not mongo:
        return jsonify({"status": "error", "reason": "MongoDB not initialized"}), 500

    try:
        raw_collection = mongo.db["asteroids_raw"]
        analysis_collection = mongo.db["asteroid_analyses"]

        pipeline_agg = [
            {"$lookup": {
                "from": "asteroid_analyses",
                "localField": "asteroid.id",
                "foreignField": "neo_reference_id",
                "as": "analysis",
            }},
            {"$match": {"analysis": {"$size": 0}}},
            {"$count": "unprocessed"},
        ]
        agg_result = list(raw_collection.aggregate(pipeline_agg))
        unprocessed_count = agg_result[0]["unprocessed"] if agg_result else 0

        analyzed_today = analysis_collection.count_documents({
            "analysis_timestamp": {
                "$gte": datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            }
        })

        high_risk_count = analysis_collection.count_documents({
            "risk_data.risk_level": {"$in": ["High", "Critical"]}
        })

        total_analyzed = analysis_collection.count_documents({})

        last_run = analysis_collection.find_one(
            sort=[("analysis_timestamp", -1)]
        )

        return jsonify({
            "status": "ok",
            "unprocessed": unprocessed_count,
            "analyzed_today": analyzed_today,
            "total_analyzed": total_analyzed,
            "high_risks": high_risk_count,
            "last_pipeline_run": (
                last_run["analysis_timestamp"].isoformat()
                if last_run else None
            ),
        }), 200

    except Exception as e:
        logger.error(f"Failed to compute pipeline stats: {e}")
        return jsonify({"status": "error", "details": str(e)}), 500

@orchestration_bp.route("/close-approaches", methods=["GET"])
def close_approaches():
    """NEOs sorted by miss distance, enriched with risk data from the Rust Engine."""
    limit = request.args.get("limit", default=10, type=int)
    mongo = current_app.extensions.get("mongo")
    if not mongo:
        return jsonify({"status": "error", "reason": "MongoDB not initialized"}), 500

    try:
        pipeline = [
            {"$unwind": "$asteroid.close_approach_data"},
            {
                "$lookup": {
                    "from": "asteroid_analyses",
                    "localField": "asteroid.id",
                    "foreignField": "neo_reference_id",
                    "as": "analysis",
                }
            },
            {
                "$project": {
                    "name": "$asteroid.name",
                    "is_hazardous": "$asteroid.is_potentially_hazardous_asteroid",
                    "close_approach_date": "$asteroid.close_approach_data.close_approach_date",
                    "miss_km": {"$toDouble": "$asteroid.close_approach_data.miss_distance.kilometers"},
                    "velocity_kps": {"$toDouble": "$asteroid.close_approach_data.relative_velocity.kilometers_per_second"},
                    "risk_level": {"$arrayElemAt": ["$analysis.risk_data.risk_level", 0]},
                    "risk_score": {"$arrayElemAt": ["$analysis.risk_data.risk_score_0_to_100", 0]},
                    "diameter_km": {"$arrayElemAt": ["$analysis.risk_data.diameter_km", 0]},
                }
            },
            {"$sort": {"miss_km": 1}},
            {"$limit": limit},
        ]

        results = list(mongo.db["asteroids_raw"].aggregate(pipeline))

        return jsonify([
            {
                "name": r.get("name", "?"),
                "is_hazardous": r.get("is_hazardous", False),
                "close_approach_date": r.get("close_approach_date", ""),
                "miss_km": round(r.get("miss_km") or 0.0),
                "velocity_kps": round(r.get("velocity_kps") or 0.0, 2),
                "risk_level": r.get("risk_level") or "Unknown",
                "risk_score": round(r.get("risk_score") or 0.0, 1),
                "diameter_km": round(r.get("diameter_km") or 0.0, 4),
            }
            for r in results
        ]), 200

    except Exception as e:
        logger.error(f"Failed to get close approaches: {e}")
        return jsonify({"status": "error", "details": str(e)}), 500


@orchestration_bp.route("/analysis/asteroids", methods=["GET"])
def list_analyzed_asteroids():

    mongo = current_app.extensions.get("mongo")
    if not mongo:
        return jsonify({"error": "MongoDB not initialized"}), 500

    limit = request.args.get("limit", default=200, type=int)
    sort_by = request.args.get("sort", default="risk_score", type=str)
    order = request.args.get("order", default="desc", type=str)

    try:
        collection = mongo.db["asteroid_analyses"]

        sort_field = {
            "risk": "risk_data.risk_score_0_to_100",
            "energy": "risk_data.impact_energy_megatons",
            "date": "analysis_timestamp",
        }.get(sort_by, "risk_data.risk_score_0_to_100")

        sort_dir = -1 if order == "desc" else 1

        cursor = (
            collection
            .find({}, {"_id": 0})
            .sort(sort_field, sort_dir)
            .limit(limit)
        )

        results = []
        for doc in cursor:
            risk = doc["risk_data"]
            results.append({
                "id": doc["neo_reference_id"],
                "name": risk["asteroid_name"],
                "risk_level": risk["risk_level"],
                "risk_score": risk["risk_score_0_to_100"],
                "energy_mt": risk["impact_energy_megatons"],
                "distance_km": risk["miss_distance_km"],
                "diameter_km": risk["diameter_km"],
                "velocity_kps": risk["velocity_kps"],
                "hazardous": risk["is_potentially_hazardous"],
                "analyzed_at": doc["analysis_timestamp"].isoformat(),
            })

        return jsonify(results), 200

    except Exception as e:
        logger.error(f"Failed to list analyzed asteroids: {e}")
        return jsonify({"error": "Internal server error"}), 500
