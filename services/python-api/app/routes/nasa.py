from datetime import date, timedelta
from flask import Blueprint, jsonify, request, current_app
from requests.exceptions import RequestException, HTTPError

from app.core.nasa_client import get_neo_feed, get_neo_feed_chunked, get_asteroid_detail
from app.utils.logger import logger

nasa_bp = Blueprint("nasa", __name__, url_prefix="/nasa")

_MAX_DATE_RANGE_DAYS = 365


def _normalize_asteroid(neo: dict, approach_date: str) -> dict:
    """Flatten a NASA NEO object into our API shape."""
    approaches = neo.get("close_approach_data", [])
    closest = approaches[0] if approaches else {}

    diameter = neo.get("estimated_diameter", {}).get("kilometers", {})
    diam_min = diameter.get("estimated_diameter_min", 0.0)
    diam_max = diameter.get("estimated_diameter_max", 0.0)

    velocity = closest.get("relative_velocity", {})
    miss = closest.get("miss_distance", {})

    return {
        "id": neo.get("id"),
        "neo_reference_id": neo.get("neo_reference_id"),
        "name": neo.get("name"),
        "nasa_jpl_url": neo.get("nasa_jpl_url"),
        "absolute_magnitude_h": neo.get("absolute_magnitude_h"),
        "is_potentially_hazardous": neo.get("is_potentially_hazardous_asteroid", False),
        "diameter_km_min": round(diam_min, 4),
        "diameter_km_max": round(diam_max, 4),
        "diameter_km_avg": round((diam_min + diam_max) / 2, 4),
        "miss_distance_km": round(float(miss.get("kilometers", 0)), 2),
        "miss_distance_lunar": round(float(miss.get("lunar", 0)), 4),
        "velocity_kps": round(float(velocity.get("kilometers_per_second", 0)), 4),
        "close_approach_date": closest.get("close_approach_date", approach_date),
        "orbiting_body": closest.get("orbiting_body", "Earth"),
    }


@nasa_bp.route("/neo/feed", methods=["GET"])
def neo_feed():
    logger.info("GET /nasa/neo/feed")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    try:
        data = get_neo_feed(start_date=start_date, end_date=end_date)
        return jsonify(data), 200
    except HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        if status == 429:
            return jsonify({"error": "NASA API rate limit reached, retry later"}), 429
        logger.error(f"NASA API HTTP error: {e}")
        return jsonify({"error": "NASA API returned an error", "details": str(e)}), 502
    except RequestException as e:
        logger.error(f"NASA API network error: {e}")
        return jsonify({"error": "Failed to connect to NASA API", "details": str(e)}), 503
    except Exception as e:
        logger.critical(f"Unexpected error in /nasa/neo/feed: {e}")
        return jsonify({"error": "Internal server error"}), 500


@nasa_bp.route("/neo/save", methods=["POST"])
def save_neo_data():
    logger.info("POST /nasa/neo/save")
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        feed = get_neo_feed(start_date=start_date, end_date=end_date)
        if not feed or "near_earth_objects" not in feed:
            return jsonify({"error": "Invalid feed from NASA"}), 502

        mongo = current_app.extensions.get("mongo")
        if not mongo:
            raise RuntimeError("Mongo extension not initialized.")

        # Deduplicate against existing records
        existing_ids: set[str] = set(
            doc.get("asteroid", {}).get("neo_reference_id", doc.get("asteroid", {}).get("id", ""))
            for doc in mongo.db["asteroids_raw"].find({}, {"asteroid.id": 1, "asteroid.neo_reference_id": 1})
        )

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

        logger.info(f"neo/save: {saved} saved, {skipped} skipped")
        return jsonify({"status": "success", "stored": saved, "skipped": skipped}), 200

    except RequestException as e:
        logger.error(f"NASA API request failed: {e}")
        return jsonify({"error": "NASA API unreachable"}), 503
    except Exception as e:
        logger.critical(f"Unexpected error in /nasa/neo/save: {e}")
        return jsonify({"error": "Internal server error"}), 500


@nasa_bp.route("/asteroids", methods=["GET"])
def list_asteroids():
    """
    Filterable asteroid list backed by NASA NEO feed.
    Supports ranges beyond 7 days via automatic chunking.

    Query params:
      start_date       YYYY-MM-DD (default: today)
      end_date         YYYY-MM-DD (default: start_date + 7 days)
      is_hazardous     true | false
      min_distance_km  float
      max_distance_km  float
      name             substring search (case-insensitive)
      sort_by          name | distance | diameter | velocity (default: distance)
      order            asc | desc (default: asc)
    """
    logger.info("GET /nasa/asteroids")

    # --- parse & validate dates ---
    start_str = request.args.get("start_date")
    end_str = request.args.get("end_date")

    try:
        start = date.fromisoformat(start_str) if start_str else date.today()
        end = date.fromisoformat(end_str) if end_str else start + timedelta(days=7)
    except ValueError:
        return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400

    if end < start:
        return jsonify({"error": "end_date must be >= start_date"}), 400

    if (end - start).days > _MAX_DATE_RANGE_DAYS:
        return jsonify({"error": f"Date range cannot exceed {_MAX_DATE_RANGE_DAYS} days"}), 400

    # --- optional filters ---
    is_hazardous_raw = request.args.get("is_hazardous")
    is_hazardous: bool | None = None
    if is_hazardous_raw is not None:
        if is_hazardous_raw.lower() not in ("true", "false"):
            return jsonify({"error": "is_hazardous must be 'true' or 'false'"}), 400
        is_hazardous = is_hazardous_raw.lower() == "true"

    min_distance_km = request.args.get("min_distance_km", type=float)
    max_distance_km = request.args.get("max_distance_km", type=float)
    name_query = request.args.get("name", "").strip().lower()

    sort_by = request.args.get("sort_by", "distance")
    order = request.args.get("order", "asc")

    if sort_by not in ("name", "distance", "diameter", "velocity"):
        return jsonify({"error": "sort_by must be one of: name, distance, diameter, velocity"}), 400
    if order not in ("asc", "desc"):
        return jsonify({"error": "order must be 'asc' or 'desc'"}), 400

    # --- fetch ---
    try:
        feed = get_neo_feed_chunked(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )
    except HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        if status == 429:
            return jsonify({"error": "NASA API rate limit reached, retry later"}), 429
        logger.error(f"NASA API HTTP error: {e}")
        return jsonify({"error": "NASA API returned an error"}), 502
    except RequestException as e:
        logger.error(f"NASA API unreachable: {e}")
        return jsonify({"error": "Failed to connect to NASA API"}), 503
    except Exception as e:
        logger.critical(f"Unexpected error in /nasa/asteroids: {e}")
        return jsonify({"error": "Internal server error"}), 500

    # --- normalize & deduplicate by asteroid id (keep smallest miss distance) ---
    seen: dict[str, dict] = {}
    for approach_date, neo_list in feed.get("near_earth_objects", {}).items():
        for neo in neo_list:
            normalized = _normalize_asteroid(neo, approach_date)
            neo_id = normalized["id"]
            if neo_id not in seen or normalized["miss_distance_km"] < seen[neo_id]["miss_distance_km"]:
                seen[neo_id] = normalized

    asteroids = list(seen.values())

    # --- filter ---
    if is_hazardous is not None:
        asteroids = [a for a in asteroids if a["is_potentially_hazardous"] == is_hazardous]

    if min_distance_km is not None:
        asteroids = [a for a in asteroids if a["miss_distance_km"] >= min_distance_km]

    if max_distance_km is not None:
        asteroids = [a for a in asteroids if a["miss_distance_km"] <= max_distance_km]

    if name_query:
        asteroids = [a for a in asteroids if name_query in (a["name"] or "").lower()]

    # --- sort ---
    sort_keys = {
        "name": lambda a: (a["name"] or "").lower(),
        "distance": lambda a: a["miss_distance_km"],
        "diameter": lambda a: a["diameter_km_avg"],
        "velocity": lambda a: a["velocity_kps"],
    }
    asteroids.sort(key=sort_keys[sort_by], reverse=(order == "desc"))

    return jsonify({
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "total": len(asteroids),
        "asteroids": asteroids,
    }), 200


@nasa_bp.route("/asteroids/<asteroid_id>", methods=["GET"])
def asteroid_detail(asteroid_id: str):
    """
    Full asteroid record from NASA NeoWS.
    Includes all historical close approaches and orbital data.
    """
    logger.info(f"GET /nasa/asteroids/{asteroid_id}")

    try:
        data = get_asteroid_detail(asteroid_id)
    except HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        if status == 404:
            return jsonify({"error": f"Asteroid {asteroid_id} not found"}), 404
        if status == 429:
            return jsonify({"error": "NASA API rate limit reached, retry later"}), 429
        logger.error(f"NASA API HTTP error for {asteroid_id}: {e}")
        return jsonify({"error": "NASA API returned an error"}), 502
    except RequestException as e:
        logger.error(f"NASA API unreachable for asteroid {asteroid_id}: {e}")
        return jsonify({"error": "Failed to connect to NASA API"}), 503
    except Exception as e:
        logger.critical(f"Unexpected error in /nasa/asteroids/{asteroid_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500

    diameter = data.get("estimated_diameter", {})
    orbital = data.get("orbital_data", {})

    close_approaches = [
        {
            "date": ca.get("close_approach_date"),
            "date_full": ca.get("close_approach_date_full"),
            "velocity_kps": round(float(ca.get("relative_velocity", {}).get("kilometers_per_second", 0)), 4),
            "velocity_kph": round(float(ca.get("relative_velocity", {}).get("kilometers_per_hour", 0)), 2),
            "miss_distance_km": round(float(ca.get("miss_distance", {}).get("kilometers", 0)), 2),
            "miss_distance_lunar": round(float(ca.get("miss_distance", {}).get("lunar", 0)), 4),
            "orbiting_body": ca.get("orbiting_body"),
        }
        for ca in data.get("close_approach_data", [])
    ]

    return jsonify({
        "id": data.get("id"),
        "neo_reference_id": data.get("neo_reference_id"),
        "name": data.get("name"),
        "nasa_jpl_url": data.get("nasa_jpl_url"),
        "absolute_magnitude_h": data.get("absolute_magnitude_h"),
        "is_potentially_hazardous": data.get("is_potentially_hazardous_asteroid", False),
        "is_sentry_object": data.get("is_sentry_object", False),
        "diameter": {
            "km_min": diameter.get("kilometers", {}).get("estimated_diameter_min"),
            "km_max": diameter.get("kilometers", {}).get("estimated_diameter_max"),
            "m_min": diameter.get("meters", {}).get("estimated_diameter_min"),
            "m_max": diameter.get("meters", {}).get("estimated_diameter_max"),
        },
        "close_approach_data": close_approaches,
        "orbital_data": {
            "orbit_id": orbital.get("orbit_id"),
            "epoch_osculation": orbital.get("epoch_osculation"),
            "eccentricity": orbital.get("eccentricity"),
            "semi_major_axis": orbital.get("semi_major_axis"),
            "inclination": orbital.get("inclination"),
            "ascending_node_longitude": orbital.get("ascending_node_longitude"),
            "orbital_period": orbital.get("orbital_period"),
            "perihelion_distance": orbital.get("perihelion_distance"),
            "aphelion_distance": orbital.get("aphelion_distance"),
            "minimum_orbit_intersection": orbital.get("minimum_orbit_intersection"),
            "orbit_determination_date": orbital.get("orbit_determination_date"),
            "orbit_class": orbital.get("orbit_class", {}).get("orbit_class_description"),
            "orbit_class_type": orbital.get("orbit_class", {}).get("orbit_class_type"),
        },
    }), 200
