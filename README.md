# AstroForge

AstroForge is a backend-focused system designed to ingest real NASA data, process it through a high-performance Rust computation engine, and expose the results through a clean Python API and a minimal Streamlit dashboard.

This project follows a backend-first philosophy and aims to build a complete Level 1 foundation before expanding to more advanced features.

---

## Overview

AstroForge consists of three main services:

1. **Python API (Flask)**  
   Handles NASA data ingestion, orchestration, communication with Rust, and exposes endpoints consumed by the dashboard.

2. **Rust Engine**  
   A dedicated microservice for scientific calculations such as simplified orbital metrics, velocity estimation, impact energy, and heuristic risk scoring.

3. **Dashboard (Streamlit)**  
   A minimal UI for viewing NASA data, analysis results, and system logs.

An infrastructure layer using Docker Compose ties everything together.

---

## Project Goals (Level 1 Scope)

- Fetch and normalize NASA NEOWS and APOD data.
- Send normalized data to the Rust computation engine.
- Return computed metrics to the Python API.
- Display data, analysis, and logs via the Streamlit dashboard.
- Keep the structure minimal until real code justifies expansion.
- Produce a complete, finished, and maintainable baseline system.

---

## Architecture

### Python API (Flask)
Responsible for:
- Fetching NASA data
- Normalizing inputs
- Calling the Rust engine
- Exposing REST endpoints
- Producing log output

Directory structure:

```
services/python-api/app/
├── routes/
├── core/
├── models/
├── utils/
└── storage/
```

---

### Rust Engine
Responsible for:
- Heavy numerical computations
- Simplified orbital math
- Impact energy calculations
- Risk scoring

Level 1 structure:

```
services/rust-engine/src/
├── main.rs
├── logic/
│   ├── orbit_math.rs
│   └── impact_energy.rs
└── domain/
    ├── asteroid.rs
    ├── orbit.rs
    └── risk.rs
```

Additional modules (api/, dto/, utils/) will be added only when required.

---

### Dashboard (Streamlit)
Provides:
- A simple interface for NASA data
- Analysis results from Rust
- Log visualization

Current structure:

```
services/dashboard/streamlit_app/
├── Main.py
└── utils/
    └── api_client.py
```

Additional pages may be introduced in later levels.

---

## Project Structure

```
project-root/
├── services/
│   ├── python-api/         # Main Python API (Flask)
│   │   ├── app/
│   │   │   ├── routes/     # NASA, Analysis, Logs
│   │   │   ├── core/       # NASA client, Rust client, Config
│   │   │   ├── models/     # Asteroid, Orbit, Analysis Result
│   │   │   ├── utils/      # Logger, Validators
│   │   │   ├── storage/    # Log files
│   │   │   └── main.py     # Flask app
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── rust-engine/        # Rust calculation engine
│   │   ├── src/
│   │   │   ├── domain/     # Asteroid, Orbit, Risk
│   │   │   ├── logic/      # Orbit math, Impact energy
│   │   │   └── main.rs     # Server setup
│   │   ├── Cargo.toml
│   │   └── Dockerfile
│   │
│   └── dashboard/          # Streamlit Dashboard
│       ├── streamlit_app/
│       │   ├── Main.py     # Main dashboard page
│       │   └── utils/      # Helper functions
│       ├── requirements.txt
│       └── Dockerfile
│
├── infra/
│   ├── docker-compose.yml
│   ├── scripts/            # start_dev.sh, rebuild.sh
│   └── env/                # Environment variables per service
│
└── docs/
    ├── architecture.md
    ├── roadmap-levels.md
    ├── api-spec-python.md
    ├── api-spec-rust.md
    └── data-flows.md
```

---

## Infrastructure

The infrastructure layer manages service orchestration and local development consistency.

Directory structure:

```
infra/
├── docker-compose.yml
├── scripts/
└── env/
```

- `docker-compose.yml`: multi-service orchestration  
- `env/`: environment variables per service  
- `scripts/`: development helpers (rebuild, start, etc.)

---

## Documentation

The `docs/` directory contains:
- `architecture.md` — high-level system overview  
- `roadmap-levels.md` — multi-phase project plan  
- `api-spec-python.md` — Python API definitions  
- `api-spec-rust.md` — Rust engine interface  
- `data-flows.md` — ingestion and analysis flows  

Documentation will expand as the codebase grows.

---

## Development Philosophy

AstroForge follows these principles:

- Backend-first development  
- Minimalism at early stages  
- Complexity added only when needed  
- Clear separation between services  
- Maintainability and readability over speed  
- Step-by-step growth toward higher levels  

No folder or module should be added without a concrete functional reason.

---

## Current Status

- All high-level directories created  
- Base scaffolding for each service in place  
- No implementation added yet  
- Level 1 begins with NASA ingestion and Rust analysis  

Progress and next steps are documented in `PROJECT_STATUS.md`.

---

## License

This project currently has no license. A license will be added once the first stable version is complete.
