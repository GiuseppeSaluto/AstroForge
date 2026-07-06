# API Specification - Python Service

Full reference for the Flask API (port 5001). For a quick overview see the
[endpoint table in the README](../README.md#api-reference).

---

## Asteroid data

### `GET /nasa/asteroids`

Filterable NEO list backed by NASA NeoWS. Automatically splits date ranges beyond the
NASA 7-day limit into chunks and aggregates results. Responses cached 5 minutes (TTLCache).

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `start_date` | `YYYY-MM-DD` | today | Range start |
| `end_date` | `YYYY-MM-DD` | start + 7 days | Range end (max 365 days from start) |
| `is_hazardous` | `true\|false` | — | Filter by hazard classification |
| `min_distance_km` | float | — | Minimum miss distance in km |
| `max_distance_km` | float | — | Maximum miss distance in km |
| `name` | string | — | Case-insensitive substring match on name |
| `sort_by` | `name\|distance\|diameter\|velocity` | `distance` | Sort field |
| `order` | `asc\|desc` | `asc` | Sort direction |

**Example**

```
GET /nasa/asteroids?start_date=2026-06-01&end_date=2026-06-30&is_hazardous=true&sort_by=distance
```

**Response**

```json
{
  "start_date": "2026-06-01",
  "end_date": "2026-06-30",
  "total": 4,
  "asteroids": [
    {
      "id": "3542519",
      "neo_reference_id": "3542519",
      "name": "(2010 PK9)",
      "nasa_jpl_url": "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=3542519",
      "absolute_magnitude_h": 21.41,
      "is_potentially_hazardous": true,
      "diameter_km_min": 0.1329,
      "diameter_km_max": 0.2972,
      "diameter_km_avg": 0.2151,
      "miss_distance_km": 4521384.12,
      "miss_distance_lunar": 11.76,
      "velocity_kps": 14.32,
      "close_approach_date": "2026-06-08",
      "orbiting_body": "Earth"
    }
  ]
}
```

---

### `GET /nasa/asteroids/<asteroid_id>`

Full asteroid record from NASA NeoWS: all historical close approaches, orbital data, and JPL link.
Response cached 5 minutes.

**Example**

```
GET /nasa/asteroids/3542519
```

**Response**

```json
{
  "id": "3542519",
  "neo_reference_id": "3542519",
  "name": "(2010 PK9)",
  "nasa_jpl_url": "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=3542519",
  "absolute_magnitude_h": 21.41,
  "is_potentially_hazardous": true,
  "is_sentry_object": false,
  "diameter": {
    "km_min": 0.1329,
    "km_max": 0.2972,
    "m_min": 132.9,
    "m_max": 297.2
  },
  "close_approach_data": [
    {
      "date": "1945-07-12",
      "date_full": "1945-Jul-12 14:21",
      "velocity_kps": 9.71,
      "velocity_kph": 34970.12,
      "miss_distance_km": 71234521.0,
      "miss_distance_lunar": 185.3,
      "orbiting_body": "Earth"
    }
  ],
  "orbital_data": {
    "orbit_id": "11",
    "eccentricity": "0.5061",
    "semi_major_axis": "1.8742",
    "inclination": "4.6523",
    "orbital_period": "936.4",
    "perihelion_distance": "0.9254",
    "aphelion_distance": "2.8231",
    "orbit_class": "Apollo",
    "orbit_determination_date": "2021-06-03"
  }
}
```

---

### `GET /nasa/neo/feed`

Raw NASA NeoWS feed proxy (max 7-day window). Returns the unmodified NASA response.

| Parameter | Type | Default |
|---|---|---|
| `start_date` | `YYYY-MM-DD` | today |
| `end_date` | `YYYY-MM-DD` | start + 7 days |

---

### `POST /nasa/neo/save`

Fetches and persists a NEO feed window to MongoDB (deduplicates by asteroid ID).

| Parameter | Type | Default |
|---|---|---|
| `start_date` | `YYYY-MM-DD` | today |
| `end_date` | `YYYY-MM-DD` | start + 7 days |

```json
{ "status": "success", "stored": 42, "skipped": 3 }
```

---

## Pipeline

### `POST /pipeline/neo/analyze`

Triggers Rust risk analysis for all unprocessed asteroids in MongoDB.

| Parameter | Type | Default |
|---|---|---|
| `limit` | int (1–1000) | 100 |

```json
{
  "status": "success",
  "statistics": { "total_fetched": 50, "processed": 48, "failed": 1, "skipped": 1 }
}
```

### `POST /pipeline/neo/analyze/<asteroid_id>`

Analyzes a single asteroid already stored in MongoDB.

```json
{
  "status": "success",
  "asteroid_id": "3542519",
  "risk_analysis": {
    "risk_level": "Low",
    "risk_score_0_to_100": 12.4,
    "impact_energy_megatons": 0.003,
    "miss_distance_km": 4521384.12
  }
}
```

### `GET /pipeline/status`

System health check — MongoDB and Rust Engine connectivity.

```json
{
  "status": "healthy",
  "components": { "mongodb": "connected", "rust_engine": "ok" }
}
```

### `GET /pipeline/stats`

Pipeline statistics for the current session.

```json
{
  "status": "ok",
  "unprocessed": 120,
  "analyzed_today": 48,
  "high_risks": 3,
  "last_pipeline_run": "2026-06-06T14:32:10+00:00"
}
```

### `GET /pipeline/analysis/asteroids`

List of analyzed asteroids sorted by risk score.

| Parameter | Type | Default |
|---|---|---|
| `limit` | int | 200 |
| `sort_by` | `risk\|energy\|date` | `risk` |
| `order` | `asc\|desc` | `desc` |

### `GET /pipeline/close-approaches`

NEOs sorted by miss distance, enriched with risk data from the Rust Engine.

| Parameter | Type | Default |
|---|---|---|
| `limit` | int | 10 |

---

## Logs

### `GET /logs`

Recent structured log entries from the Python API.

| Parameter | Type | Default |
|---|---|---|
| `limit` | int | 100 |
| `level` | `DEBUG\|INFO\|WARNING\|ERROR\|CRITICAL` | — |
| `query` | string | — |

```json
[
  {
    "timestamp": "2026-06-06 14:32:10",
    "level": "INFO",
    "logger": "app.routes.nasa",
    "message": "Cache HIT — NEO feed 2026-06-01→2026-06-07"
  }
]
```
