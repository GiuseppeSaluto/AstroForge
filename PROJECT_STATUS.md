# AstroForge — Project Status

*Last updated: December 3, 2025*

This document tracks the current implementation state, validated architecture, and next steps for Level 1.

---

## 1. Overview

AstroForge is a microservice system for asteroid tracking and risk analysis:

1. **Python Flask API**: NASA data ingestion, Rust engine coordination, MongoDB persistence
2. **Rust Engine**: Scientific calculations (orbital metrics, velocity, impact energy, risk scoring)
3. **Streamlit Dashboard**: Visualization of NASA data, analysis results, logs
4. **Infrastructure**: Docker Compose orchestration, MongoDB for data persistence

---

## 2. Implementation Status

### ✅ Python API (`services/python-api`)

**Completed:**
- ✅ Flask application factory pattern (`main.py`)
- ✅ NASA NEO Feed client with configurable date ranges (`core/nasa_client.py`)
- ✅ Rust engine HTTP client (`core/rust_client.py`)
- ✅ Configuration management with environment variables (`core/config.py`)
- ✅ MongoDB client with Flask integration (`core/mongodb.py`)
  - Collections: `nasa_feeds`, `asteroid_analyses`, `asteroids_raw`
  - Indexes for date, asteroid.id, stored_at
  - CRUD operations: save/retrieve NASA feeds and raw asteroids
- ✅ Logging infrastructure with file + console output (`utils/logger.py`)
  - Log path: `services/python-api/logs/python_api.log`
- ✅ NASA route: GET `/nasa/neo/feed` with date filters (`routes/nasa.py`)
- ✅ Analysis route: POST `/analysis/asteroids/feed` (`routes/analysis.py`)

**Structure:**
```
app/
├── main.py
├── core/
│   ├── config.py
│   ├── nasa_client.py
│   ├── rust_client.py
│   └── mongodb.py
├── routes/
│   ├── nasa.py
│   ├── analysis.py
│   └── logs.py (placeholder)
├── models/
│   └── asteroid.py (placeholder)
└── utils/
    ├── logger.py
    └── validators.py (placeholder)
```

**Pending:**
- Route implementation for logs viewing
- Model definitions (asteroid, orbit, analysis_result)
- Data validators
- Integration with MongoDB for storing/retrieving analysis results

---

### ⚠️ Rust Engine (`services/rust-engine`)

**Status:** Structure defined, **no implementation yet**

**Planned Structure:**
```
src/
├── main.rs (HTTP server placeholder)
├── domain/
│   ├── asteroid.rs
│   ├── orbit.rs
│   └── risk.rs
└── logic/
    ├── orbit_math.rs
    └── impact_energy.rs
```

**Required Implementation:**
1. HTTP server (Axum/Actix-web) with `/analysis/asteroids/feed` endpoint
2. Domain models for asteroid, orbit, risk assessment
3. Orbital mechanics calculations (velocity, semi-major axis, eccentricity)
4. Impact energy estimation
5. Risk scoring heuristic

---

### ⚠️ Dashboard (`services/dashboard`)

**Status:** Structure created, **no implementation yet**

**Planned:**
- Streamlit single-page app (`Main.py`)
- API client for Python backend (`utils/api_client.py`)
- Display NASA NEO feed data
- Visualize analysis results from Rust
- Show logs from Python API

---

### 🔧 Infrastructure (`infra/`)

**Available:**
- Docker Compose configuration (`docker-compose.yml`)
- Environment template files (`.env.example` for each service)
- Startup scripts (`start_dev.sh`, `rebuild.sh`)

**Task Definitions (VS Code):**
- `cargo build (rust-engine)`
- `cargo run (rust-engine)`
- `Run Python API`
- `Run Streamlit Dashboard`
- `Start All Services`
- `Docker Compose Up/Down`

---

## 3. Data Flow (Current)

```
[NASA API] → [Python: nasa_client] → [MongoDB: nasa_feeds/asteroids_raw]
                    ↓
[Python: analysis route] → [Rust: /analysis/asteroids/feed] → Analysis Result
                    ↓
[MongoDB: asteroid_analyses] ← [Python stores result]
                    ↓
[Dashboard] ← queries → [Python API] → [MongoDB]
```

---

## 4. MongoDB Collections

| Collection | Purpose | Key Indexes |
|------------|---------|-------------|
| `nasa_feeds` | Raw NASA NEO feed responses | `retrieved_at`, `feed_start_date`, `feed_end_date` |
| `asteroids_raw` | Individual asteroid objects by date | `date`, `asteroid.id`, `stored_at` |
| `asteroid_analyses` | Rust analysis results | `neo_reference_id`, `analysis_timestamp` |

---

## 5. API Endpoints

### Python API (Port 5000)

| Method | Endpoint | Purpose | Status |
|--------|----------|---------|--------|
| GET | `/nasa/neo/feed` | Fetch NASA NEO data | ✅ Implemented |
| POST | `/analysis/asteroids/feed` | Send data to Rust for analysis | ✅ Implemented |
| GET | `/logs` | Retrieve system logs | ⚠️ Placeholder |

### Rust Engine (Port 8080)

| Method | Endpoint | Purpose | Status |
|--------|----------|---------|--------|
| POST | `/analysis/asteroids/feed` | Analyze asteroid feed | ❌ Not implemented |

---

## 6. Next Steps (Priority Order)

### Phase 1: Complete Rust Engine
1. Set up Axum/Actix HTTP server in `main.rs`
2. Define domain structs (Asteroid, Orbit, RiskAssessment)
3. Implement orbital calculations in `logic/orbit_math.rs`
4. Implement impact energy in `logic/impact_energy.rs`
5. Create `/analysis/asteroids/feed` endpoint handler
6. Return JSON response compatible with Python API

### Phase 2: Enhance Python API
1. Implement `/logs` route for dashboard access
2. Define models in `models/asteroid.py`, `models/orbit.py`
3. Add MongoDB persistence for analysis results
4. Implement validation utilities

### Phase 3: Build Dashboard
1. Implement `Main.py` with Streamlit
2. Create API client for Python backend
3. Display NASA feed data
4. Visualize Rust analysis results
5. Show real-time logs

### Phase 4: Integration & Testing
1. Test end-to-end data flow
2. Verify Docker Compose setup
3. Test all environment configurations
4. Document deployment process

---

## 7. Deferred for Later Levels

- Advanced prediction models
- Machine learning integration
- Multi-page dashboard complexity
- Performance optimizations
- Caching layers
- Additional NASA API endpoints (APOD implemented but not integrated)

---

## 8. Configuration Notes

**Environment Variables Required:**
- `NASA_API_KEY`: NASA API access key
- `RUST_ENGINE_URL`: Rust service endpoint (default: `http://localhost:8080`)
- `MONGO_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
- `MONGO_DB`: Database name (default: `astroforge_db`)
- `LOG_DIRECTORY`: Log output path (default: `./logs`)

**Log Output:**
- File: `services/python-api/logs/python_api.log`
- Console: stdout/stderr during Flask runtime

---

## 9. Key Design Decisions

- **Minimal structure**: No premature abstraction, grow organically
- **MongoDB for persistence**: Flexible schema for NASA data and analysis results
- **Rust for computation**: Performance-critical calculations isolated from I/O
- **Single-page dashboard**: Start simple, expand only when needed
- **Environment-based config**: 12-factor app principles for deployment flexibility
