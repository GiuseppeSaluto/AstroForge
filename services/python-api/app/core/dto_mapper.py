from typing import Optional
from app.models.asteroid import Asteroid
from app.utils.logger import logger


def map_nasa_raw_to_asteroid(raw_nasa_data: dict) -> Optional[Asteroid]:

    try:
        asteroid_id = (raw_nasa_data.get("id") or "").strip()
        name = (raw_nasa_data.get("name") or "Unknown").strip()

        if not asteroid_id:
            logger.warning("Skipping asteroid with empty ID")
            return None

        # NASA sometimes sends `null` for a field instead of omitting it,
        # e.g. "estimated_diameter": null. `.get(key, {})` only applies the
        # default when the key is *missing* — if the key is present but
        # None, `or {}` is needed to avoid a crash on the next `.get()`.
        diameter_info = (raw_nasa_data.get("estimated_diameter") or {}).get("kilometers", {}) or {}
        diameter_min = diameter_info.get("estimated_diameter_min", 0.0)
        diameter_max = diameter_info.get("estimated_diameter_max", 0.0)
        diameter_avg = (diameter_min + diameter_max) / 2.0

        if diameter_avg <= 0.0:
            logger.warning(f"Asteroid {asteroid_id} has invalid diameter, skipping")
            return None

        close_approach_data = raw_nasa_data.get("close_approach_data") or []
        if not close_approach_data:
            logger.warning(f"Asteroid {asteroid_id} missing close approach data, skipping")
            return None

        first_approach = close_approach_data[0] or {}

        velocity_info = first_approach.get("relative_velocity") or {}
        velocity_kps = float(velocity_info.get("kilometers_per_second", 0.0))
        if velocity_kps <= 0.0:
            logger.warning(f"Asteroid {asteroid_id} has non-physical velocity ({velocity_kps}), skipping")
            return None


        miss_distance_info = first_approach.get("miss_distance") or {}
        miss_distance_km = float(miss_distance_info.get("kilometers", 0.0))
        
        approach_date = first_approach.get("close_approach_date", "")
        orbiting_body = first_approach.get("orbiting_body", "Earth")
        
        is_hazardous = raw_nasa_data.get("is_potentially_hazardous_asteroid", False)
        
        absolute_magnitude = raw_nasa_data.get("absolute_magnitude_h", 0.0)
        
        return Asteroid(
            id=asteroid_id,
            name=name,
            absolute_magnitude_h=absolute_magnitude,
            diameter_km=diameter_avg,
            velocity_kps=velocity_kps,
            distance_km=miss_distance_km,
            is_potentially_hazardous=is_hazardous,
            close_approach_date=approach_date,
            orbiting_body=orbiting_body,
        )
        
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        logger.error(f"Error mapping NASA data to Asteroid: {e}")
        return None


def map_mongo_document_to_asteroid(mongo_doc: dict) -> Optional[Asteroid]:
    raw_asteroid = mongo_doc.get("asteroid")
    
    if not raw_asteroid:
        logger.warning("MongoDB document missing 'asteroid' field")
        return None
    
    return map_nasa_raw_to_asteroid(raw_asteroid)
