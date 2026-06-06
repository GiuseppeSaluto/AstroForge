# AstroForge

Backend system for tracking and analyzing Near-Earth Objects using real NASA data.
Ingests NEO data, processes it through a Rust risk-analysis engine, persists results to MongoDB,
and exposes a documented REST API consumed by a Textual terminal dashboard.

---

## Architecture

```
NASA NeoWS API
      │
      ▼
┌─────────────────────────────────┐
│  Python API  (Flask · port 5001) │  ← proxy, cache, chunking, filtering
│   core/nasa_client  (TTLCache)   │
│   routes/nasa  GET /asteroids    │
└───────────┬─────────────────────┘
            │  pipeline trigger
            ▼
┌─────────────────────────────────┐
│  Rust Engine (Axum · port 8080)  │  ← impact energy, risk scoring
│   /api/process/asteroid          │
└───────────┬─────────────────────┘
            │  persist
            ▼
┌─────────────────────────────────┐
│  MongoDB  (port 27017)           │
│   asteroids_raw                  │
│   asteroid_analyses              │
│   nasa_feeds                     │
└───────────┬─────────────────────┘
            │  read
            ▼
┌─────────────────────────────────┐
│  Textual Dashboard (local TUI)   │
│   Home · Asteroids · Charts      │
│   Pipeline · Logs                │
└─────────────────────────────────┘
```

---

## Quick Start

### Docker (recommended)

```bash
# 1 — create env file
cp infra/env/python.env.example infra/env/python.env
#    → set NASA_API_KEY inside python.env

# 2 — build and start all services
cd infra
docker compose up --build
```

Services started:

| Service | URL |
|---|---|
| Python API | `http://localhost:5001` |
| Rust Engine | `http://localhost:8080` |
| MongoDB | `localhost:27017` |

### Local dev (manual)

```bash
# MongoDB
mongod --dbpath /tmp/mongodb --logpath /tmp/mongodb.log --fork

# Rust Engine
cd services/rust-engine && cargo run

# Python API
cd services/python-api
source venv/bin/activate
python -m app.main

# Dashboard (separate terminal)
cd services/dashboard
source venv/bin/activate
python -m app.main
```

#### First-time venv setup

```bash
cd services/python-api && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd ../dashboard       && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

Or use the one-command launcher:

```bash
./infra/scripts/start_dev.sh
```

---

## API Reference — Python API (port 5001)

### Asteroid data

#### `GET /nasa/asteroids`

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

#### `GET /nasa/asteroids/<asteroid_id>`

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

#### `GET /nasa/neo/feed`

Raw NASA NeoWS feed proxy (max 7-day window). Returns the unmodified NASA response.

| Parameter | Type | Default |
|---|---|---|
| `start_date` | `YYYY-MM-DD` | today |
| `end_date` | `YYYY-MM-DD` | start + 7 days |

---

#### `POST /nasa/neo/save`

Fetches and persists a NEO feed window to MongoDB (deduplicates by asteroid ID).

| Parameter | Type | Default |
|---|---|---|
| `start_date` | `YYYY-MM-DD` | today |
| `end_date` | `YYYY-MM-DD` | start + 7 days |

```json
{ "status": "success", "stored": 42, "skipped": 3 }
```

---

### Pipeline

#### `POST /pipeline/neo/analyze`

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

#### `POST /pipeline/neo/analyze/<asteroid_id>`

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

#### `GET /pipeline/status`

System health check — MongoDB and Rust Engine connectivity.

```json
{
  "status": "healthy",
  "components": { "mongodb": "connected", "rust_engine": "ok" }
}
```

#### `GET /pipeline/stats`

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

#### `GET /pipeline/analysis/asteroids`

List of analyzed asteroids sorted by risk score.

| Parameter | Type | Default |
|---|---|---|
| `limit` | int | 200 |
| `sort_by` | `risk\|energy\|date` | `risk` |
| `order` | `asc\|desc` | `desc` |

---

### Logs

#### `GET /logs`

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

---

## API Reference — Rust Engine (port 8080)

#### `GET /api/health`

Returns `"ok"` when the engine is running.

#### `POST /api/process/asteroid`

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

---

## Dashboard — Keyboard Shortcuts

| Key | Screen |
|---|---|
| `h` | Home — system status + quick actions |
| `a` | Asteroids — analyzed risk table |
| `c` | Charts — miss distance scatter + size distribution bar chart |
| `p` | Pipeline — trigger analysis, live stats |
| `l` | Logs — real-time log viewer |
| `q` | Quit |

The dashboard reads `API_BASE_URL` (default `http://localhost:5001`) — point it at a deployed
instance by exporting the variable before launch:

```bash
API_BASE_URL=https://your-deployed-api.fly.dev python -m app.main
```

---

## Project Structure

```
services/
├── python-api/           Flask API — NASA proxy, caching, pipeline orchestration
│   ├── app/
│   │   ├── core/         nasa_client, cache, mongodb, rust_client, pipeline, config
│   │   ├── routes/       nasa, orchestration, logs, analysis
│   │   ├── models/       Asteroid domain model
│   │   └── utils/        Structured logger
│   ├── Dockerfile
│   └── requirements.txt
│
├── rust-engine/          Axum microservice — impact physics + risk scoring
│   ├── src/
│   │   ├── api/          HTTP handlers
│   │   ├── domain/       Asteroid, RiskResult, errors
│   │   ├── dto/          Validated request/response types
│   │   └── logic/        Impact energy, risk algorithm
│   └── Dockerfile
│
└── dashboard/            Textual TUI — local visualization
    └── app/
        ├── screens/      Home, Asteroids, Charts, Pipeline, Logs
        ├── widgets/      StatsPanel, AsteroidTable, LogViewer
        └── client/       API client with retry strategy

infra/
├── docker-compose.yml    Full stack orchestration
├── env/                  Environment variable templates
└── scripts/              Local dev launcher
```

---

## Caching

All NASA API calls are cached in-memory with a 5-minute TTL (thread-safe `cachetools.TTLCache`).
Cache keys include the full parameter set so different date ranges are cached independently.
The cache is intentionally in-process — no Redis dependency for the challenge scope.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NASA_API_KEY` | Yes | NASA API key (api.nasa.gov) |
| `MONGO_URI` | Yes | MongoDB connection string |
| `MONGO_DB` | No | Database name (default: `astroforge_db`) |
| `RUST_ENGINE_URL` | Yes | Rust engine base URL |
| `LOG_DIRECTORY` | No | Log file path (default: `./storage/logs`) |
| `REQUEST_TIMEOUT` | No | NASA HTTP timeout in seconds (default: 30) |
| `DEBUG` | No | Flask debug mode (default: false) |

Copy `infra/env/python.env.example` → `infra/env/python.env` and fill in values before starting.

---

## License

No license — challenge submission only.
