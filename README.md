# AstroForge ☄️

[![CI](https://github.com/GiuseppeSaluto/AstroForge/actions/workflows/ci.yml/badge.svg)](https://github.com/GiuseppeSaluto/AstroForge/actions/workflows/ci.yml)

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

## API Reference

Full request/response examples live in `docs/`:
[Python API spec](docs/api-spec-python.md) · [Rust Engine spec](docs/api-spec-rust.md)

**Python API — port 5001**

| Endpoint | Description |
|---|---|
| `GET /nasa/asteroids` | Filterable, normalized NEO list (hazard, distance, name, sort) |
| `GET /nasa/asteroids/<id>` | Full asteroid record — close approaches + orbital data |
| `GET /nasa/neo/feed` | Raw NASA NeoWS feed proxy (max 7-day window) |
| `POST /nasa/neo/save` | Fetch + persist a feed window to MongoDB (deduplicated) |
| `POST /pipeline/neo/analyze` | Run Rust risk analysis on all unprocessed asteroids |
| `POST /pipeline/neo/analyze/<id>` | Analyze a single stored asteroid |
| `GET /pipeline/status` | Health check — MongoDB + Rust Engine connectivity |
| `GET /pipeline/stats` | Pipeline statistics (unprocessed, analyzed, high-risk counts) |
| `GET /pipeline/analysis/asteroids` | List analyzed asteroids, sorted by risk/energy/date |
| `GET /pipeline/close-approaches` | NEOs sorted by miss distance, enriched with risk data |
| `GET /logs` | Recent structured log entries |

**Rust Engine — port 8080**

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness check |
| `POST /api/process/asteroid` | Impact-physics risk analysis for one asteroid |
| `POST /api/process/batch` | Same, for a batch of 1–500 asteroids |

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

Licensed under the MIT License — see LICENSE for details
