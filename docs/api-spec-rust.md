# API Specification - Rust Engine

Full reference for the Axum service (port 8080), mounted under `/api`. For a quick
overview see the [endpoint table in the README](../README.md#api-reference).

---

### `GET /api/health`

Returns `"ok"` when the engine is running.

---

### `POST /api/process/batch`

Runs impact-physics risk analysis on a JSON array of 1–500 asteroid DTOs.

**Request body** — array of:

```json
{
  "id": "3542519",
  "name": "(2010 PK9)",
  "diameter_avg_km": 0.2151,
  "relative_velocity_kps": 14.32,
  "miss_distance_km": 4521384.12,
  "is_potentially_hazardous": true
}
```

Unknown extra fields are ignored, so older clients that send more fields still work.

**Response** — `200 OK`. Entries that fail domain validation (empty ID, non-positive
diameter, negative velocity or miss distance) don't fail the batch: they are reported
in `errors` while the valid ones are scored in `results`.

```json
{
  "results": [
    {
      "asteroid_id": "3542519",
      "asteroid_name": "(2010 PK9)",
      "risk_level": "Low",
      "risk_score_0_to_100": 12.4,
      "impact_energy_joules": 1.26e13,
      "impact_energy_megatons": 0.003,
      "diameter_km": 0.2151,
      "velocity_kps": 14.32,
      "miss_distance_km": 4521384.12,
      "is_potentially_hazardous": true
    }
  ],
  "errors": [
    { "id": "999", "details": "Invalid diameter: -1 km (must be > 0)" }
  ]
}
```

Returns `400 Bad Request` for an empty array or a batch larger than 500.
