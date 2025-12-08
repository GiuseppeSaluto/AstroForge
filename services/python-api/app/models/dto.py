class AsteroidDTO:
    id: str
    name: str
    absolute_magnitude_h: float
    diameter_min_km: float
    diameter_max_km: float
    diameter_avg_km: float
    close_approach_date: str
    relative_velocity_kps: float
    miss_distance_km: float
    is_potentially_hazardous: bool
    orbiting_body: str
    
    def __init__(self, raw_doc: dict) -> None:
        if not raw_doc:
            raise ValueError("Raw document for AsteroidDTO cannot be None or empty.")
        self.id = raw_doc.get("id", "")
        self.name = raw_doc.get("name", "")
        self.absolute_magnitude_h = raw_doc.get("absolute_magnitude_h", 0.0)
        
        diameter_info = raw_doc.get("estimated_diameter", {}).get("kilometers", {})
        self.diameter_min_km = diameter_info.get("estimated_diameter_min", 0.0)
        self.diameter_max_km = diameter_info.get("estimated_diameter_max", 0.0)
        self.diameter_avg_km = (self.diameter_min_km + self.diameter_max_km) / 2
        
        close_approach_data = raw_doc.get("close_approach_data", [])
        if close_approach_data:
            first_approach = close_approach_data[0]
            self.close_approach_date = first_approach.get("close_approach_date", "")
            relative_velocity_info = first_approach.get("relative_velocity", {})
            self.relative_velocity_kps = float(relative_velocity_info.get("kilometers_per_second", 0.0))
            miss_distance_info = first_approach.get("miss_distance", {})
            self.miss_distance_km = float(miss_distance_info.get("kilometers", 0.0))
            self.orbiting_body = first_approach.get("orbiting_body", "")
        else:
            self.close_approach_date = ""
            self.relative_velocity_kps = 0.0
            self.miss_distance_km = 0.0
            self.orbiting_body = ""
        
        self.is_potentially_hazardous = raw_doc.get("is_potentially_hazardous_asteroid", False)
        
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "absolute_magnitude_h": self.absolute_magnitude_h,
            "diameter_min_km": self.diameter_min_km,
            "diameter_max_km": self.diameter_max_km,
            "diameter_avg_km": self.diameter_avg_km,
            "close_approach_date": self.close_approach_date,
            "relative_velocity_kps": self.relative_velocity_kps,
            "miss_distance_km": self.miss_distance_km,
            "is_potentially_hazardous": self.is_potentially_hazardous,
            "orbiting_body": self.orbiting_body,
        }