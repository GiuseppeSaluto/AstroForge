# AstroForge — Project Status

This document tracks the current state of the project, its validated architecture, and the next actionable steps for Level 1 (Foundational Version).

---

## 1. Overview

AstroForge is a microservice-based system composed of:

1. A Python Flask API for ingesting NASA data, coordinating analysis, and providing endpoints for the dashboard.
2. A Rust computation engine responsible for scientific calculations (orbital metrics, velocity estimates, impact energy, and simplified risk scoring).
3. A Streamlit dashboard for displaying NASA data, analysis results, and system logs.
4. A shared infrastructure layer using Docker Compose to orchestrate services.

The goal of Level 1 is to deliver a complete and reliable core system without premature complexity.

---

## 2. Current Architecture (after consolidation)

### services/python-api
- Purpose: Orchestrate data ingestion, call NASA APIs, communicate with the Rust engine, and expose HTTP endpoints for the dashboard.
- Structure:
  - `routes/` (kept intentionally small: nasa.py, analysis.py, logs.py)
  - `core/` (nasa_client.py, rust_client.py, config.py)
  - `models/` (data representations used internally)
  - `utils/` (logging, validation)
  - `storage/` (local log output)
- Status: Folder structure created. No implementation yet.

### services/rust-engine
- Purpose: Perform heavy mathematical computation and return results to the Python API.
- Structure (simplified based on advice):
  - `main.rs`
  - `logic/` (orbit_math.rs, impact_energy.rs)
  - `domain/` (asteroid.rs, orbit.rs, risk.rs)
- The following folders will be added only when necessary:
  - `api/`, `dto/`, `utils/`
- Status: Folder structure created. Code implementation not started.

### services/dashboard
- Purpose: Provide a minimal and functional UI for NASA data, Rust analysis, and logs.
- Structure (reduced for Level 1):
  - `streamlit_app/Main.py`
  - `streamlit_app/utils/api_client.py`
- Additional pages will be added only after the core workflow is functional.
- Status: Structure created. To be expanded later.

### infra/
- Contains docker-compose configuration, helper scripts, and environment variable files.
- Status: Placeholder structure established.

### docs/
- Contains architecture, roadmap, API specs, and dataflow documentation.
- Status: Documentation skeleton in place.

---

## 3. Removed or Postponed Elements

Based on feedback, the following components were removed or postponed to avoid premature complexity:

- Rust folders `api/`, `dto/`, and `utils/` (to be added when needed)
- Streamlit multi-page structure (consolidated into a single entry point)
- Python API extra modules not required for Level 1
- Any “prediction” or advanced modeling logic (reserved for future levels)

This ensures the project remains achievable and focused.

---

## 4. Next Steps (in strict order)

1. Implement NASA client and basic ingestion endpoint in Python.
2. Implement Rust computation logic for:
   - velocity estimation  
   - simplified orbit metrics  
   - impact energy  
   - risk score (heuristic)
3. Implement Rust HTTP service with a single `/analyze` endpoint.
4. Connect Python API to Rust engine using rust_client.
5. Implement Main.py in Streamlit to visualize:
   - NASA raw data  
   - analysis results  
   - log output
6. Finalize Docker Compose integration.

---

## 5. Notes

The project structure is intentionally minimal for Level 1.  
No new folders should be added until code naturally requires them.