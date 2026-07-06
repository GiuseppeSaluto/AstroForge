# API Specification - Rust Engine

Full reference for the Axum service (port 8080), mounted under `/api`. For a quick
overview see the [endpoint table in the README](../README.md#api-reference).

---

### `GET /api/health`

Returns `"ok"` when the engine is running.

---

### `POST /api/process/asteroid`

Runs impact-physics risk analysis on a single asteroid DTO.

**Request body** — normalized asteroid object with mass, velocity, and close-approach data.

**Response**

```json
{
  "asteroid_id": "3542519",
  "asteroid_name": "(2010 PK9)",
  "risk_level": "Low",
  "risk_score_0_to_100": 12.4,
  "impact_energy_megatons": 0.003,
  "diameter_km": 0.2151,
  "velocity_kps": 14.32,
  "miss_distance_km": 4521384.12,
  "is_potentially_hazardous": true
}
```

Returns `400 Bad Request` if the DTO fails domain validation (empty ID, non-positive
diameter, negative velocity or miss distance).

---

### `POST /api/process/batch`

Same as `/api/process/asteroid`, but takes a JSON array (1–500 entries) and returns an
array of results. Entries that fail validation are silently dropped from the response
rather than failing the whole batch — the caller (the Python pipeline) reconciles which
IDs are missing from the response to know what was skipped.

Returns `400 Bad Request` for an empty array or a batch larger than 500.
